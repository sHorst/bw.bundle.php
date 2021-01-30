PHP Bundle
----------

This bundle checks the METADATA for php content and applies them.

It is capable to install multiple php versions.

Install
-------

To make this bundle work, you need to insert the libs/convertToPhp.py to the bw repository. This can be done with this command:

```
ln -s ../bundles/php/libs/convertToPhp.py libs/convertToPhp.py
```

Dependencies
------------
Packages defined in ```metadata.py``` and installed via [apt-Bundle](https://github.com/sHorst/bw.bundle.apt).

Demo Metadata
-------------

```python
metadata = {
    'php': {
        'default_version': '7.3',
        'global_modules': {
            'zip': {
                'enabled': True,
            },
            'intl': {
                'enabled': True,
            },
        },
        'versions': {
            '7.3': {
                'modules': {
                    'mysqli': {
                        'enabled': True,
                        'apt': 'php7.3-mysql',
                    },
                    'mbstring': {
                        'enabled': True,
                    }
                },
            },
        },
    },
}
```