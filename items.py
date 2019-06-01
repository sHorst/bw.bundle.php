php_version = '5'
php_config_path = '/etc/php'

if node.os == 'debian' and node.os_version[0] >= 9:
    php_version = '7.0'
    php_config_path = '/etc/php/7.0'

actions = {}
pkg_apt = {
    "php{}".format(php_version): {
        "installed": True,
    },
    "php{}-curl".format(php_version): {
        "installed": True,
    },
    "php{}-gd".format(php_version): {
        "installed": True,
    },
    "php{}-cgi".format(php_version): {
        "installed": True,
    },
    "php{}-dev".format(php_version): {
        "installed": True,
    },
    'php-pear': {
        "installed": True,
    },
    # 'libcurl3-openssl-dev': {
    #     "installed": True,
    # },
}

git_deploy = {}

if node.os == 'debian':
    if node.os_version[0] < 9:
        # PHP is not thread save, so install preforked
        pkg_apt["apache2-mpm-prefork"] = {"installed": True, }
        pkg_apt["apache2-mpm-event"] = {"installed": False, }
        pkg_apt["apache2-mpm-worker"] = {"installed": False, }
    elif node.os_version[0] == 9:
        # install php7.0-xml to have utf8-decode/utf8-encode
        pkg_apt['php7.0-xml'] = {'installed': True}

needs = []
pecl = False
for mod_name, mod_config in node.metadata.get('php', {}).get('modules', {}).items():
    if mod_config.get('pecl', False):
        pecl = True
        mod_peclname = mod_config.get('pecl_name', mod_name)
        git = mod_config.get('git', None)

        if git:
            actions['git_clone_pecl_{}'.format(mod_name)] = {
                'command': 'cd /tmp && rm -rf pecl_{name} && git clone {git} pecl_{name}'.format(
                    git=git,
                    name=mod_name
                ),
                'unless': 'test -f {path}/mods-available/{name}.ini'.format(path=php_config_path, name=mod_name),
            }
            actions['pecl_{}_phpize'.format(mod_name)] = {
                'command': 'cd /tmp/pecl_{name} && /usr/bin/phpize7.0'.format(name=mod_name),
                'needs': [
                    'action:git_clone_pecl_{}'.format(mod_name),
                    'pkg_apt:build-essential'
                ],
                'unless': 'test -f {path}/mods-available/{name}.ini || test -f /tmp/pecl_{name}/configure'.format(
                    path=php_config_path,
                    name=mod_name
                ),
            }
            actions['pecl_{}_configure'.format(mod_name)] = {
                'command': 'cd /tmp/pecl_{name} && ./configure'.format(name=mod_name),
                'needs': [
                    'action:pecl_{}_phpize'.format(mod_name)
                ],
                'unless': 'test -f {path}/mods-available/{name}.ini || test -f /tmp/pecl_{name}/Makefile'.format(
                    path=php_config_path,
                    name=mod_name
                ),
            }
            actions['pecl_{}_make_install'.format(mod_name)] = {
                'command': 'cd /tmp/pecl_{name} && make && make install'.format(name=mod_name),
                'needs': [
                    'action:pecl_{}_configure'.format(mod_name)
                ],
                'unless': 'test -f {path}/mods-available/{name}.ini'.format(
                    path=php_config_path,
                    name=mod_name
                ),
            }
            actions['pecl_{}_create_ini'.format(mod_name)] = {
                'command': 'echo "; configuration for php bbcode module\n'
                           '; priority=20\n'
                           'extension={name}.so" > {path}/mods-available/{name}.ini'.format(
                               path=php_config_path,
                               name=mod_name,
                           ),
                'needs': [
                    'action:pecl_{}_make_install'.format(mod_name),
                ],
                'unless': 'test -f {path}/mods-available/{name}.ini'.format(
                    path=php_config_path,
                    name=mod_name
                ),
            }

            needs += ['action:pecl_{}_create_ini'.format(mod_name), ]
        else:
            actions['pecl_install_{}'.format(mod_peclname)] = {
                'command': '/usr/bin/pecl install {}'.format(mod_name),
                'unless': 'test -f {path}/mods-available/{name}.ini'.format(path=php_config_path, name=mod_name),
                'needs': ['pkg_apt:build-essential'],
                'cascade_skip': False,
            }

            needs += [
                'action:pecl_install_{}'.format(mod_peclname)
            ]

    elif mod_config.get('pear', False):
        mod_pearname = mod_config.get('pear_name', mod_name)
        actions['pear_install_{}'.format(mod_pearname)] = {
            'command': '/usr/bin/pear install {}'.format(mod_name),
            'unless': 'test -f {path}/mods-available/{name}.ini'.format(path=php_config_path, name=mod_name),
            'needs': ['pkg_apt:php-pear'],
            'cascade_skip': False,
        }

        needs += [
            'action:pear_install_{}'.format(mod_pearname)
        ]

    else:
        mod_aptname = mod_config.get('apt', 'php{}-{}'.format(php_version, mod_name))
        pkg_apt[mod_aptname] = {'installed': True, }

        needs += [
            'pkg_apt:{}'.format(mod_aptname)
        ]

    if mod_config.get('enabled', False):
        actions['enable_mod_{}'.format(mod_name)] = {
            'command': '/usr/sbin/phpenmod {}'.format(mod_name),
            'unless': 'test -f {path}/cli/conf.d/*-{name}.ini'.format(path=php_config_path, name=mod_name),
            'needs': needs,
            'cascade_skip': False,
        }
    else:
        actions['disable_mod_{}'.format(mod_name)] = {
            'command': '/usr/sbin/phpdismod {}'.format(mod_name),
            'unless': 'test ! -f {path}/cli/conf.d/*-{name}.ini'.format(path=php_config_path, name=mod_name),
            'needs': needs,
            'cascade_skip': False,
        }

if pecl:
    pkg_apt['build-essential'] = {'installed': True, }
