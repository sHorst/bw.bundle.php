defaults = {}

php_version = '5'
php_config_path = '/etc/php'
if node.os == 'debian':
    if node.os_version[0] == 9:
        php_version = '7.0'
        php_config_path = '/etc/php/7.0'
    elif node.os_version[0] == 10:
        php_version = '7.3'
        php_config_path = '/etc/php/7.3'

defaults['php'] = {
    'version': php_version,
    'modules': {
        "curl": {'enabled': True, },
        "gd": {'enabled': True, },
    },
    'config_path': php_config_path,
}


@metadata_reactor
def add_apt_packages(metadata):
    if not node.has_bundle("apt"):
        raise DoNotRunAgain

    packages = {}

    php_version = metadata.get('php/version')

    # install php version for current os
    packages['php{version}'.format(version=php_version)] = {'installed': True}

    # install cgi and dev packages
    packages['php{version}-cgi'.format(version=php_version)] = {'installed': True}
    packages['php{version}-dev'.format(version=php_version)] = {'installed': True}

    if node.os == 'debian':
        if node.os_version[0] < 9:
            # PHP is not thread save, so install preforked
            packages["apache2-mpm-prefork"] = {"installed": True, }
            packages["apache2-mpm-event"] = {"installed": False, }
            packages["apache2-mpm-worker"] = {"installed": False, }
        else:
            # install php{}-xml to have utf8-decode/utf8-encode
            packages['php{}-xml'.format(php_version)] = {'installed': True}

    pecl = False
    pear = False
    for mod_name, mod_config in metadata.get('php/modules', {}).items():
        if mod_config.get('pecl', False):
            pecl = True
        elif mod_config.get('pear', False):
            pear = True
        else:
            mod_aptname = mod_config.get('apt', 'php{}-{}'.format(php_version, mod_name))
            packages[mod_aptname] = {'installed': True, }

    if pear:
        packages['php-pear'] = {'installed': True, }
    if pecl:
        packages['build-essential'] = {'installed': True, }

    return {
        'apt': {
            'packages': packages,
        }
    }
