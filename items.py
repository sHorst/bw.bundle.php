actions = {}
git_deploy = {}
files = {}


if node.has_bundle('apt'):
    files['/etc/apt/sources.list.d/php.list'] = {
        'content': 'deb [signed-by=/usr/share/keyrings/php.gpg] https://packages.sury.org/php/ {release_name} main\n'.format(
            release_name=node.metadata.get(node.os).get('release_name')
        ),
        'content_type': 'text',
        'needs': ['file:/usr/share/keyrings/php.gpg', ],
        'triggers': ["action:force_update_apt_cache", ],
    }
    files['/usr/share/keyrings/php.gpg'] = {
        'content_type': 'binary',
    }

svc_systemd = {}

for php_version, php_config in node.metadata.get('php', {}).get('versions', {}).items():
    php_config_path = php_config['config_path']

    svc_systemd[f'php{php_version}-fpm.service'] = {
        'needs': [f'pkg_apt:php{php_version}-fpm']
    }

    custom_config = node.metadata.get('php/custom_config', {})
    custom_config.update(php_config.get('custom_config', {}))

    for t, content in custom_config.items():
        files[f'/etc/php/{php_version}/{t}/conf.d/99-custom.ini'] = {
            'content': '\n'.join(sorted([f'{k}={v}' for k, v in content.items()])) + '\n',
            'content_type': 'text',
            'triggers': [
                f'svc_systemd:php{php_version}-fpm.service:restart',
            ]
        }

    needs = []
    for mod_name, mod_config in php_config.get('modules', {}).items():
        if mod_config.get('pecl', False):
            mod_pecl_name = mod_config.get('pecl_name', mod_name)
            git = mod_config.get('git', None)

            if git:
                git_deploy[f'/tmp/pecl_{mod_pecl_name}'] = {
                    'repo': git,
                    'rev': mod_config.get('rev', 'master'),
                    # not needed, if we already have an ini
                    # TODO: make this dependent on different content
                    'unless': f'test -f {php_config_path}/mods-available/{mod_name}.ini',
                }
                # actions[f'git_clone_pecl_{mod_name}_php{php_version}'] = {
                #     'command': f'cd /tmp && rm -rf pecl_{mod_pecl_name} && git clone {git} pecl_{mod_pecl_name}',
                # }

                actions[f'pecl_{mod_name}_phpize{php_version}'] = {
                    'command': f'cd /tmp/pecl_{mod_pecl_name} && /usr/bin/phpize{php_version}',
                    'needs': [
                        f'git_deploy:/tmp/pecl_{mod_pecl_name}',
                        f'pkg_apt:php{php_version}',
                        'pkg_apt:build-essential'
                    ],
                    # not needed, if we already have an ini
                    # TODO: make this dependent on different content
                    'unless': f'test -f {php_config_path}/mods-available/{mod_name}.ini '
                               f'|| test -f /tmp/pecl_{mod_name}/configure',
                }
                actions[f'pecl_{mod_name}_configure_php{php_version}'] = {
                    'command': f'cd /tmp/pecl_{mod_pecl_name} && ./configure',
                    'needs': [
                        f'action:pecl_{mod_name}_phpize{php_version}',
                    ],
                    # not needed, if we already have an ini
                    # TODO: make this dependent on different content
                    'unless': f'test -f {php_config_path}/mods-available/{mod_name}.ini '
                               f'|| test -f /tmp/pecl_{mod_pecl_name}/Makefile',
                }
                actions[f'pecl_{mod_name}_make_install_php{php_version}'] = {
                    'command': f'cd /tmp/pecl_{mod_pecl_name} && make && make install',
                    'needs': [
                        f'action:pecl_{mod_name}_configure_php{php_version}',
                    ],
                    # not needed, if we already have an ini
                    # TODO: make this dependent on different content
                    'unless': f'test -f {php_config_path}/mods-available/{mod_name}.ini',
                }
                files[f'{php_config_path}/mods-available/{mod_name}.ini'] = {
                    'content': '\n'.join([
                        f"; configuration for php {mod_name} module",
                        "; priority=20",
                        f"extension={mod_name}.so",
                    ]) + '\n',
                    'needs': [
                        f'action:pecl_{mod_name}_make_install_php{php_version}',
                    ],
                    'cascade_skip': False,
                    # do not overwrite file, if it exists
                    'unless': f'test -f {php_config_path}/mods-available/{mod_name}.ini',
                }

                needs += [
                    f'file:{php_config_path}/mods-available/{mod_name}.ini',
                ]
            else:
                # TODO: install certain version
                actions[f'pecl_install_{mod_name}'] = {
                    'command': f'/usr/bin/pecl install {mod_pecl_name}',
                    'unless': f'/usr/bin/pecl list | grep -q {mod_pecl_name}',
                    'needs': [
                        'pkg_apt:build-essential',
                        'pkg_apt:pkg-php-tools',
                    ],
                    'cascade_skip': False,
                }

                files[f'{php_config_path}/mods-available/{mod_name}.ini'] = {
                    'content': '\n'.join([
                        f"; configuration for php {mod_name} module",
                        "; priority=20",
                        f"extension={mod_name}.so",
                    ]) + '\n',
                    'needs': [
                        f'action:pecl_install_{mod_name}',
                    ],
                    'cascade_skip': False,
                    # do not overwrite file, if it exists
                    'unless': f'test -f {php_config_path}/mods-available/{mod_name}.ini',
                }

                needs += [
                    f'action:pecl_install_{mod_name}',
                ]

        elif mod_config.get('pear', False):
            mod_pear_name = mod_config.get('pear_name', mod_name)
            actions[f'pear_install_{mod_name}_php{php_version}'] = {
                'command': f'/usr/bin/pear install {mod_pear_name}',
                'unless': f'test -f {php_config_path}/mods-available/{mod_name}.ini',
                'needs': ['pkg_apt:php-pear', ],
                'cascade_skip': False,
            }

            needs += [
                f'action:pear_install_{mod_name}_php{php_version}',
            ]

        else:
            needs += [
                'pkg_apt:{}'.format(mod_config.get('apt', f'php{php_version}-{mod_name}'))
            ]

        # install module into php
        if mod_config.get('enabled', False):
            actions[f'enable_mod_{mod_name}_php{php_version}'] = {
                'command': f'/usr/sbin/phpenmod -v {php_version} {mod_name}',
                'unless': f'test -f {php_config_path}/cli/conf.d/*-{mod_name}.ini',
                'needs': needs,
                'cascade_skip': False,
                'triggers': [
                    f'svc_systemd:php{php_version}-fpm.service:restart',
                ]
            }
        else:
            actions[f'disable_mod_{mod_name}_php{php_version}'] = {
                'command': f'/usr/sbin/phpdismod -v {php_version} {mod_name}',
                'unless': f'test ! -f {php_config_path}/cli/conf.d/*-{mod_name}.ini',
                'needs': needs,
                'cascade_skip': False,
                'triggers': [
                    f'svc_systemd:php{php_version}-fpm.service:restart',
                ]
            }
