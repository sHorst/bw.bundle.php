
@metadata_processor
def default_php_metadata(metadata):
    php_version = '5'
    php_config_path = '/etc/php'
    if node.os == 'debian':
        if node.os_version[0] == 9:
            php_version = '7.0'
            php_config_path = '/etc/php/7.0'
        elif node.os_version[0] == 10:
            php_version = '7.3'
            php_config_path = '/etc/php/7.3'


    default_metadata = {
            'php': {
                'version': php_version,
                'modules': {
                    "curl": {'enabled': True, },
                    "gd": {'enabled': True, },
                },
                'config_path': php_config_path,
            }
        }

    return default_metadata, DONE, DEFAULTS


@metadata_processor
def add_apt_packages(metadata):
    # if we did not add the version, just wait
    if 'php' not in metadata or 'version' not in metadata['php']:
        return metadata, RUN_ME_AGAIN

    if 'php' not in metadata or 'modules' not in metadata['php']:
        return metadata, RUN_ME_AGAIN

    if node.has_bundle("apt"):
        metadata.setdefault('apt', {})
        metadata['apt'].setdefault('packages', {})

        php_version = metadata['php']['version']

        # install php version for current os
        metadata['apt']['packages']['php{version}'.format(version=php_version)] = {'installed': True}

        # install cgi and dev packages
        metadata['apt']['packages']['php{version}-cgi'.format(version=php_version)] = {'installed': True}
        metadata['apt']['packages']['php{version}-dev'.format(version=php_version)] = {'installed': True}

        if node.os == 'debian':
            if node.os_version[0] < 9:
                # PHP is not thread save, so install preforked
                metadata['apt']["apache2-mpm-prefork"] = {"installed": True, }
                metadata['apt']["apache2-mpm-event"] = {"installed": False, }
                metadata['apt']["apache2-mpm-worker"] = {"installed": False, }
            else:
                # install php{}-xml to have utf8-decode/utf8-encode
                metadata['apt']['php{}-xml'.format(php_version)] = {'installed': True}

        pecl = False
        pear = False
        for mod_name, mod_config in metadata['php'].get('modules', {}).items():
            if mod_config.get('pecl', False):
                pecl = True
            elif mod_config.get('pear', False):
                pear = True
            else:
                mod_aptname = mod_config.get('apt', 'php{}-{}'.format(php_version, mod_name))
                metadata['apt']['packages'][mod_aptname] = {'installed': True, }

        if pear:
            metadata['apt']['packages']['php-pear'] = {'installed': True, }
        if pecl:
            metadata['apt']['packages']['build-essential'] = {'installed': True, }


    return metadata, DONE
