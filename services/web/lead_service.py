"""Validation and durable registration; integrations can consume this boundary later."""
import re
import uuid
from sqlalchemy.orm import Session
from models import Lead

BUSINESSES = {'retail', 'restaurants', 'hotels', 'workshops', 'industry', 'wholesale', 'services', 'startups'}
SOLUTIONS = {'web', 'ecommerce', 'erp', 'ai', 'industry', 'infrastructure'}
CHOICES = {'yes', 'no', 'unsure'}

class InvalidLead(ValueError):
    pass

def validate(payload):
    if not isinstance(payload, dict):
        raise InvalidLead('invalid_fields')
    def field(name, minimum, maximum):
        value = payload.get(name)
        if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum or '\x00' in value:
            raise InvalidLead('invalid_fields')
        return value.strip()
    result = {
        'name': field('name', 2, 120),
        'email': field('email', 3, 254),
        'description': field('description', 20, 5000),
    }
    if not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', result['email']):
        raise InvalidLead('invalid_email')
    for name, choices in [('business_type', BUSINESSES), ('solution_type', SOLUTIONS), ('online_payments', CHOICES), ('ai', CHOICES), ('integration', CHOICES)]:
        value = payload.get(name)
        if not isinstance(value, str) or value not in choices:
            raise InvalidLead('invalid_fields')
        result[name] = value
    result['features'] = field('features', 0, 2000) if 'features' in payload else ''
    result['integration_details'] = field('integration_details', 0, 1000) if 'integration_details' in payload else ''
    lang = payload.get('lang', 'es')
    if not isinstance(lang, str) or lang not in ('es', 'en', 'it'):
        raise InvalidLead('invalid_fields')
    result['language'] = lang
    if payload.get('privacy_consent') is not True:
        raise InvalidLead('privacy_required')
    return result

def register(engine, values):
    reference = str(uuid.uuid4())
    with Session(engine) as session:
        session.add(Lead(id=reference, **values))
        session.commit()
    return reference
