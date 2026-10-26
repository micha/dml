"""Whitelist for this lab's exact JSON fixture language, NOT an HCL parser.
Only string variables, literal strings and exact var/resource-id references.
"""
import json
import re

LABEL = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')
VAR = re.compile(r'\$\{var\.([A-Za-z_][A-Za-z0-9_]*)\}\Z')

class InvalidFixture(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise InvalidFixture(message)

def object_(value, message):
    require(isinstance(value, dict), message)
    return value

def load(data):
    def pairs(items):
        value = {}
        for k, v in items:
            require(k not in value, 'duplicate JSON key')
            value[k] = v
        return value
    try:
        return object_(json.loads(data, object_pairs_hook=pairs), 'non-object JSON')
    except (ValueError, TypeError) as e:
        raise InvalidFixture(str(e)) from e

def literal(value):
    require(isinstance(value, str) and '${' not in value and '%{' not in value,
            'unsupported evaluation expression/input')

def fixture(config, inputs):
    require(set(config) <= {'resource','variable','output'}, 'unsupported configuration')
    variables = object_(config.get('variable', {}), 'malformed variables')
    for name, spec in variables.items():
        require(LABEL.fullmatch(name) is not None, 'unsupported variable label')
        object_(spec, 'malformed variable')
        require(set(spec) <= {'type','default','sensitive'} and spec.get('type') == 'string'
                and spec.get('sensitive', False) is False, 'unsupported variable')
        if 'default' in spec:
            literal(spec['default'])
    require(set(inputs) <= set(variables), 'unknown variable input')
    for value in inputs.values():
        literal(value)
    require(all('default' in spec or name in inputs for name,spec in variables.items()), 'missing variable input')
    resources = object_(config.get('resource', {}), 'malformed resources')
    require(set(resources) <= {'terraform_data'}, 'unsupported resource')
    specs = object_(resources.get('terraform_data', {}), 'malformed resource instances')
    for name, spec in specs.items():
        require(LABEL.fullmatch(name) is not None, 'unsupported resource label')
        object_(spec, 'malformed resource effects')
        require(set(spec) <= {'input','triggers_replace','lifecycle'}, 'unsupported resource effects')
        lifecycle = object_(spec.get('lifecycle', {}), 'malformed lifecycle')
        require(set(lifecycle) <= {'prevent_destroy'} and
                all(type(v) is bool for v in lifecycle.values()), 'unsupported lifecycle')
        for key in ('input','triggers_replace'):
            if key not in spec:
                continue
            value = spec[key]
            if isinstance(value,str) and VAR.fullmatch(value):
                require(VAR.fullmatch(value)[1] in variables, 'unknown variable reference')
            else:
                literal(value)
    outputs = object_(config.get('output', {}), 'malformed outputs')
    require(set(outputs) == {'dml_manifest'}, 'missing/unsupported manifest output')
    output = object_(outputs['dml_manifest'], 'malformed output')
    require(set(output) <= {'value','sensitive'} and output.get('sensitive', False) is False,
            'secret/unsupported manifest')
    manifest = object_(output.get('value'), 'malformed resource census')
    addresses = {'terraform_data.' + name for name in specs}
    require(set(manifest) == addresses, 'incomplete resource census')
    require(all(value == '${'+address+'.id}' for address,value in manifest.items()),
            'malformed resource census identity expression')
    return addresses

def plan_configuration(module, planned_inputs):
    """Check the emitted JSON fixture's saved-plan config, not general HCL ASTs."""
    require(set(module) <= {'outputs','resources','variables'}, 'unsupported plan module fields')
    specs = {}
    for r in module.get('resources', []):
        require(r.get('mode') == 'managed' and r.get('type') == 'terraform_data'
                and r.get('provider_config_key') == 'terraform'
                and r.get('address') == 'terraform_data.'+r.get('name','')
                and not r.get('provisioners'), 'unsupported plan effects')
        name = r['name']
        require(name not in specs, 'duplicate plan configuration resource')
        spec = {}
        for key,expr in object_(r.get('expressions', {}), 'malformed plan expressions').items():
            require(set(expr) <= {'constant_value','references'} and 'constant_value' in expr,
                    'unsupported plan evaluation expression')
            spec[key] = expr['constant_value']
        specs[name] = spec
    outputs = {}
    for name, spec in object_(module.get('outputs', {}), 'malformed plan outputs').items():
        require(set(spec) <= {'expression','sensitive'}, 'unsupported plan output fields')
        expr = object_(spec.get('expression'), 'missing plan output expression')
        require(set(expr) <= {'constant_value','references'} and 'constant_value' in expr,
                'unsupported plan manifest expression')
        outputs[name] = {'value':expr['constant_value'], 'sensitive':spec.get('sensitive',False)}
    # Variable values are captured inside plan bytes; do not take new CLI/env inputs.
    inputs = {k:v['value'] for k,v in object_(planned_inputs, 'malformed planned inputs').items()}
    return fixture({'resource':{'terraform_data':specs},'variable':module.get('variables',{}),
                    'output':outputs}, inputs)
