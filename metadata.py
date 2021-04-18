from bundlewrap.utils.dicts import merge_dict

defaults = {}

default_php_version = '5'
if node.os == 'debian':
    if node.os_version[0] == 9:
        default_php_version = '7.0'
    elif node.os_version[0] == 10:
        default_php_version = '7.3'

defaults['php'] = {
    'default_version': default_php_version,
    'global_modules': {
        "curl": {'enabled': True, },
        "gd": {'enabled': True, },
    },
}


@metadata_reactor
def config_path(metadata):
    versions = {}
    for version, version_config in metadata.get('php/versions', {}).items():
        if version == '5':
            php_config_path = '/etc/php'
        else:
            php_config_path = f'/etc/php/{version}'

        versions[version] = {
            'config_path': php_config_path,
        }

    return {
        'php': {
            'versions': versions,
        }
    }


@metadata_reactor
def move_old_php_config_to_versions(metadata):
    version = metadata.get('php/version', None)

    # this is ether set, or defaults to the default set here
    if version is None:
        return {}

    return {
        'php': {
            'default_version': version,
            'versions': {
                version: {
                    'modules': metadata.get('php/modules', {}),
                },
            }
        }
    }


@metadata_reactor
def add_php_to_apache_config(metadata):
    if not node.has_bundle('apache'):
        raise DoNotRunAgain

    vhosts = {}
    for vhost_name, vhost in metadata.get('apache/vhosts', {}).items():
        if vhost.get('php', None) is not None:
            vhosts[vhost_name] = {
                'additional_config': {
                    'php': [
                        '<FilesMatch \\.php$>',
                        '  SetEnvIf Authorization .+ HTTP_AUTHORIZATION=$0',  # Make Auth work
                        '  SetHandler "proxy:unix:/var/run/php/php{version}-fpm.sock|fcgi://localhost"'.format(
                            version=vhost['php']
                        ),
                        '</FilesMatch>',
                    ],
                }
            }

    return {
        'apache': {
            'vhosts': vhosts,
        }
    }


@metadata_reactor
def copy_global_packages_into_all_versions(metadata):
    versions = {}

    for php_version, php_config in metadata.get('php/versions').items():
        modules = merge_dict(
            metadata.get('php/global_modules', {}),
            php_config.get('modules', {}),
        )

        versions[php_version] = {
            'modules': modules,
        }

    return {
        'php': {
            'versions': versions,
        }
    }


@metadata_reactor
def add_apt_packages(metadata):
    if not node.has_bundle("apt"):
        raise DoNotRunAgain

    pecl = False
    pear = False
    packages = {}
    for php_version, php_config in metadata.get('php/versions').items():
        # install php version for current os
        packages['php{version}'.format(version=php_version)] = {
            'installed': True,
            'needs': ['file:/etc/apt/sources.list.d/php.list', ],
        }

        # install cgi and dev packages
        packages['php{version}-cgi'.format(version=php_version)] = {
            'installed': True,
            'needs': ['file:/etc/apt/sources.list.d/php.list', ],
        }
        packages['php{version}-fpm'.format(version=php_version)] = {
            'installed': True,
            'needs': ['file:/etc/apt/sources.list.d/php.list', ],
        }
        packages['php{version}-dev'.format(version=php_version)] = {
            'installed': True,
            'needs': ['file:/etc/apt/sources.list.d/php.list', ],
        }

        if node.os == 'debian':
            if node.os_version[0] < 9:
                # PHP is not thread save, so install preforked
                packages["apache2-mpm-prefork"] = {"installed": True, }
                packages["apache2-mpm-event"] = {"installed": False, }
                packages["apache2-mpm-worker"] = {"installed": False, }
            else:
                # install php{}-xml to have utf8-decode/utf8-encode
                packages['php{}-xml'.format(php_version)] = {
                    'installed': True,
                    'needs': ['file:/etc/apt/sources.list.d/php.list', ],
                }

        for mod_name, mod_config in php_config.get('modules', {}).items():
            if mod_config.get('pecl', False):
                pecl = True
            elif mod_config.get('pear', False):
                pear = True
            else:
                packages[mod_config.get('apt', f'php{php_version}-{mod_name}')] = {
                    'installed': True,
                    'needs': ['file:/etc/apt/sources.list.d/php.list', ],
                }

    if pear:
        packages['php-pear'] = {
            'installed': True,
            'needs': ['file:/etc/apt/sources.list.d/php.list', ],
        }
    if pecl:
        packages['build-essential'] = {
            'installed': True,
            'needs': ['file:/etc/apt/sources.list.d/php.list', ],
        }
        packages['pkg-php-tools'] = {
            'installed': True,
            'needs': ['file:/etc/apt/sources.list.d/php.list', ],
        }

    return {
        'apt': {
            'packages': packages,
        }
    }
