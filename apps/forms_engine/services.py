from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from jsonschema import Draft202012Validator
from .models import DataSource
ALLOWED_FIELD_TYPES={'text','textarea','email','tel','number','date','datetime','select','multiselect','checkbox','radio','file'}
def validate_schema_definition(module,schema):
    if not isinstance(schema,dict):raise ValidationError('Schema must be a JSON object.')
    steps=schema.get('steps',[])
    if module=='ticket' and len(steps)!=4:raise ValidationError('Ticket form schemas must contain exactly four configurable steps.')
    keys=set()
    for step in steps:
        if not isinstance(step,dict) or not step.get('title'):raise ValidationError('Every step needs a title.')
        for field in step.get('fields',[]):
            key=field.get('key')
            if not key or key in keys:raise ValidationError(f'Duplicate/missing field key: {key!r}')
            keys.add(key)
            if field.get('type','text') not in ALLOWED_FIELD_TYPES:raise ValidationError(f'Unsupported field type: {field.get("type")}')
            if field.get('datasource') and not DataSource.objects.filter(code=field['datasource'],is_active=True).exists():raise ValidationError(f'Unknown datasource: {field["datasource"]}')
    return True
def resolve_datasource(code):
    source=DataSource.objects.get(code=code,is_active=True); config=source.config or {}
    if source.kind==DataSource.Kind.STATIC:return config.get('values',[])
    label=config.get('model','')
    if label not in settings.ALYUSR_ALLOWED_DATASOURCE_MODELS:raise ValidationError('Datasource model is not allowlisted.')
    model=apps.get_model(label); value_field=config.get('value_field','pk'); label_field=config.get('label_field','name')
    return [{'value':str(getattr(o,value_field)),'label':str(getattr(o,label_field))} for o in model.objects.all()[:500]]
def visible_schema_for_user(form_version,user,organization=None):
    roles={'super_admin'} if user.is_superuser else set()
    if user.is_authenticated:
        memberships=user.organization_memberships.filter(is_active=True)
        if organization:memberships=memberships.filter(organization=organization)
        roles.update(memberships.values_list('role',flat=True))
    schema={**(form_version.schema or {})}; out=[]
    for step in schema.get('steps',[]):
        fields=[]
        for field in step.get('fields',[]):
            visible=set(field.get('visible_roles') or [])
            if visible and not roles & visible:continue
            copied=dict(field); editable=set(copied.get('editable_roles') or []); copied['readonly']=bool(editable and not roles & editable)
            if copied.get('datasource'):copied['options']=resolve_datasource(copied['datasource'])
            fields.append(copied)
        out.append({**step,'fields':fields})
    schema['steps']=out; return schema
def validate_submission(schema,data):
    properties={}; required=[]
    for step in schema.get('steps',[]):
        for field in step.get('fields',[]):
            key=field['key']; typ=field.get('type','text'); properties[key]={'type':'number' if typ=='number' else 'boolean' if typ=='checkbox' else 'array' if typ=='multiselect' else 'string'}
            if field.get('required'):required.append(key)
    validator=Draft202012Validator({'type':'object','properties':properties,'required':required,'additionalProperties':True}); errors={'.'.join(map(str,e.path)) or '__all__':e.message for e in validator.iter_errors(data)}; return not errors,errors
