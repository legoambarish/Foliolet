"""Fail-closed response shape gate. Cryptographic checking remains in Java and proof-core.js."""
import re
import unicodedata
from datetime import datetime


def validate_success(result):
    flags = ('verified', 'proofValid', 'signatureValid', 'anchorMatches', 'current', 'policyActive')
    if not isinstance(result, dict) or any(result.get(k) is not True for k in flags):
        raise ValueError('Verification did not explicitly pass every check')
    if not isinstance(result.get('message'), str):
        raise ValueError('Malformed verification result')


def shape(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        raise ValueError('Malformed proof object')


def text(value, limit, empty=False):
    if (not isinstance(value, str) or len(value.encode('utf-16-le')) // 2 > limit
            or (not empty and not value) or re.search(r'[\x00-\x1f\x7f-\x9f]', value)):
        raise ValueError('Malformed text')
    whitespace = ' \u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2008\u2009\u200a\u2028\u2029\u205f\u3000'
    if value != unicodedata.normalize('NFC', value.strip(whitespace)):
        raise ValueError('Noncanonical text')


def path(value):
    text(value, 100)
    if not re.fullmatch(r'[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*', value):
        raise ValueError('Malformed fact path')


def claim_value(kind, value):
    text(value, 1000)
    if kind == 'decimal':
        if not re.fullmatch(r'-?[0-9]{1,30}(\.[0-9]{1,12})?', value):
            raise ValueError('Malformed decimal')
        whole, _, fraction = value.lstrip('-').partition('.')
        whole, fraction = whole.lstrip('0') or '0', fraction.rstrip('0')
        canonical = ('-' if value.startswith('-') and (whole != '0' or fraction) else '') + whole
        canonical += '.' + fraction if fraction else ''
        if value != canonical:
            raise ValueError('Noncanonical decimal')
    elif kind == 'boolean':
        if value not in ('true', 'false'):
            raise ValueError('Noncanonical boolean')
    elif kind == 'date':
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
            raise ValueError('Malformed date')
        year, month, day = map(int, value.split('-'))
        # Java LocalDate and the browser support proleptic Gregorian year zero.
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        days = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
        if not 1 <= month <= 12 or not 1 <= day <= days[month - 1]:
            raise ValueError('Invalid calendar date')
    elif kind != 'string':
        raise ValueError('Unsupported type')


def integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('Malformed integer')


def hex_value(value, size):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]{%d}' % (size*2), value):
        raise ValueError('Malformed hex')


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.0{1,9})?Z', value):
        raise ValueError('Malformed timestamp')
    datetime.fromisoformat(value.replace('Z', '+00:00'))


def validate_bundle(b):
    shape(b, 'format credentialId credentialVersion merkleRoot leafCount anchor provenance presentation claims envelopeHash platformSignature')
    if b['format'] != 'salted-merkle-keccak-v1':
        raise ValueError('Unknown format')
    for k in ('credentialId', 'merkleRoot', 'envelopeHash'):
        hex_value(b[k], 32)
    hex_value(b['platformSignature'], 65)
    integer(b['credentialVersion'], 1, 2147483647)
    integer(b['leafCount'], 1, 128)
    a, p, v = b['anchor'], b['presentation'], b['provenance']
    shape(a, 'contract operator chainId documentCommitment provenanceDigest provenanceCode anchoredAt txHash')
    for k in ('contract', 'operator'):
        hex_value(a[k], 20)
    for k in ('documentCommitment', 'provenanceDigest'):
        hex_value(a[k], 32)
    if a['txHash'] is not None:
        hex_value(a['txHash'], 32)
    integer(a['chainId'], 1, 9007199254740991)
    integer(a['provenanceCode'], 0, 1)
    timestamp(a['anchoredAt'])
    shape(p, 'grantId verifierLabel purpose nonce createdAt expiresAt oneTime')
    if not isinstance(p['grantId'], str) or not re.fullmatch(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}', p['grantId']):
        raise ValueError('Malformed grant ID')
    text(p['verifierLabel'], 150)
    text(p['purpose'], 250)
    hex_value(p['nonce'], 32)
    timestamp(p['createdAt'])
    timestamp(p['expiresAt'])
    if type(p['oneTime']) is not bool:
        raise ValueError('Malformed release policy')
    shape(v, 'level explanation firstReceivedAt lastReceivedAt observations observedChanges enrollmentMatchesFirst agentId')
    if v['level'] not in ('SELF_ENROLLED', 'FIRST_SEEN_TRACKED'):
        raise ValueError('Unsupported provenance')
    if a['provenanceCode'] != (1 if v['level'] == 'FIRST_SEEN_TRACKED' else 0):
        raise ValueError('Inconsistent provenance')
    text(v['explanation'], 4000)
    integer(v['observations'], 0, 2147483647)
    for k in ('observedChanges', 'enrollmentMatchesFirst'):
        if type(v[k]) is not bool:
            raise ValueError('Malformed provenance flag')
    for k in ('firstReceivedAt', 'lastReceivedAt'):
        if v[k] is not None:
            timestamp(v[k])
    if v['agentId'] is not None:
        text(v['agentId'], 100)
    if not isinstance(b['claims'], list) or not 1 <= len(b['claims']) <= b['leafCount']:
        raise ValueError('Malformed claims')
    indices, paths = set(), set()
    for c in b['claims']:
        shape(c, 'leaf proof')
        l = c['leaf']
        shape(l, 'path label type value derivedFrom salt index')
        path(l['path'])
        text(l['label'], 100)
        claim_value(l['type'], l['value'])
        text(l['derivedFrom'], 100, empty=True)
        if l['derivedFrom']:
            path(l['derivedFrom'])
        integer(l['index'], 0, b['leafCount']-1)
        hex_value(l['salt'], 32)
        if l['index'] in indices or l['path'] in paths:
            raise ValueError('Duplicate claim')
        indices.add(l['index'])
        paths.add(l['path'])
        if not isinstance(c['proof'], list) or len(c['proof']) != (b['leafCount']-1).bit_length():
            raise ValueError('Malformed path')
        for step in c['proof']:
            shape(step, 'sibling side')
            hex_value(step['sibling'], 32)
            if step['side'] not in ('LEFT', 'RIGHT'):
                raise ValueError('Malformed direction')


def recognized_threshold(leaf):
    return (leaf.get('path') == 'education.cgpa_at_least_8_5'
            and leaf.get('type') == 'boolean' and leaf.get('value') in ('true', 'false')
            and leaf.get('label') == 'CGPA at least 8.5'
            and leaf.get('derivedFrom') == 'education.cgpa')
