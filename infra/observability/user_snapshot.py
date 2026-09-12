"""Read-only product inventory → aggregate BigQuery snapshot (no UID/email stored).

Uses personal gcloud credentials locally, ADC on a dedicated Cloud Run Job.
Only --apply writes analytics data. Never writes Auth, Firestore or GCS.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request

PROJECT = 'gen-lang-client-0842206246'
BASE = f'https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}'


def api(method, url, body=None):
    if os.environ.get('CLOUD_RUN_JOB'):
        import google.auth
        from google.auth.transport.requests import Request
        creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        creds.refresh(Request())
        token = creds.token
    else:
        token = subprocess.check_output(['gcloud', 'auth', 'print-access-token',
            '--account=hardikuppal.hu@gmail.com'], text=True).strip()
    request = urllib.request.Request(url, method=method, headers={
        'Authorization': 'Bearer ' + token, 'x-goog-user-project': PROJECT,
        'Content-Type': 'application/json',
    }, data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def paged(url, items_key, page_key='nextPageToken'):
    result, token = [], ''
    while True:
        page = api('GET', url + ('&pageToken=' + urllib.parse.quote(token, safe='') if token else ''))
        result.extend(page.get(items_key, []))
        token = page.get(page_key)
        if not token:
            return result


def decode(value):
    if 'mapValue' in value:
        return {k: decode(v) for k, v in value['mapValue'].get('fields', {}).items()}
    if 'arrayValue' in value:
        return [decode(v) for v in value['arrayValue'].get('values', [])]
    return next(iter(value.values()), None)


def collect():
    users = paged(f'https://identitytoolkit.googleapis.com/v1/projects/{PROJECT}/accounts:batchGet?maxResults=1000', 'users')
    collections = {}
    for name in ('user_profiles', 'garments', 'magazine_feeds'):
        # Projection deliberately excludes images, descriptions, locations and results.
        fields = {'user_profiles': ['style_analysis.color.status', 'style_analysis.fit.status', 'analysis_quality'],
                  'garments': ['user_id'], 'magazine_feeds': ['user_id']}[name]
        url = f'https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/wardrub/documents/{name}?pageSize=1000'
        for field in fields:
            url += '&mask.fieldPaths=' + field
        docs = paged(url, 'documents')
        collections[name] = {d['name'].rsplit('/', 1)[-1]: {k: decode(v) for k, v in d.get('fields', {}).items()} for d in docs}
    # Object names only, not photo bytes or signed URLs.
    objects = paged('https://storage.googleapis.com/storage/v1/b/wardrub-assets-1/o?prefix=users/&maxResults=1000&fields=items(name),nextPageToken', 'items')
    return summarize(users, collections, [o['name'] for o in objects])


def summarize(users, collections, objects):
    counts = Counter(total_registered=len(users))
    signup_days = Counter()
    garments = Counter(d.get('user_id') for key, d in collections['garments'].items() if not key.startswith('mock-'))
    feeds = {d.get('user_id') for d in collections['magazine_feeds'].values()}
    names = set(objects)
    profiles = collections['user_profiles']
    for user in users:
        uid = user['localId']
        if user.get('createdAt'):
            from zoneinfo import ZoneInfo
            day = datetime.fromtimestamp(int(user['createdAt']) / 1000, ZoneInfo('Asia/Kolkata')).date().isoformat()
            signup_days[day] += 1
        if user.get('disabled'):
            counts['disabled_accounts'] += 1
            continue
        counts['enabled_accounts'] += 1
        counts['with_avatar'] += f'users/{uid}/avatar.png' in names
        counts['with_any_garment'] += garments[uid] > 0
        counts['with_ten_garments'] += garments[uid] >= 10
        counts['with_profile'] += uid in profiles
        counts['with_saved_magazine'] += uid in feeds
        counts['ten_garments_without_saved_magazine'] += garments[uid] >= 10 and uid not in feeds
        counts['ten_garments_without_profile'] += garments[uid] >= 10 and uid not in profiles
        progress = profiles.get(uid, {}).get('style_analysis') or {}
        counts['color_ready'] += progress.get('color', {}).get('status') == 'ready'
        counts['fit_ready'] += progress.get('fit', {}).get('status') == 'ready'
    metrics = ['total_registered', 'enabled_accounts', 'disabled_accounts', 'with_avatar',
               'with_any_garment', 'with_ten_garments', 'with_profile', 'with_saved_magazine',
               'ten_garments_without_saved_magazine', 'ten_garments_without_profile', 'color_ready', 'fit_ready']
    return {'counts': {key: counts[key] for key in metrics}, 'signup_days': dict(sorted(signup_days.items()))}


def query(sql, parameters=None):
    job = api('POST', BASE + '/queries', {'query': sql, 'useLegacySql': False, 'location': 'US',
        'maximumBytesBilled': '1000000000', 'timeoutMs': 20000,
        'parameterMode': 'NAMED', 'queryParameters': parameters or []})
    while not job.get('jobComplete'):
        time.sleep(2)
        job = api('GET', BASE + '/queries/' + job['jobReference']['jobId'] + '?location=US')
    if job.get('errors'):
        raise RuntimeError('BigQuery query failed')


def save(report):
    # A whole snapshot is one row, so a partial inventory is never published.
    query('''CREATE TABLE IF NOT EXISTS `gen-lang-client-0842206246.wardrub_events.user_snapshots`
      (collected_at TIMESTAMP, payload STRING)
      PARTITION BY DATE(collected_at) OPTIONS(partition_expiration_days=180)''')
    query('INSERT INTO `gen-lang-client-0842206246.wardrub_events.user_snapshots` VALUES(CURRENT_TIMESTAMP(), @payload)', [
        {'name': 'payload', 'parameterType': {'type': 'STRING'}, 'parameterValue': {'value': json.dumps(report)}}])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    report = collect()
    if args.apply:
        save(report)
    print(json.dumps({'written': args.apply, **report}, indent=2))
