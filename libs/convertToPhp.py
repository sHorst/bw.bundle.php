def convert_to_php(value, indent=4):
    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, int):
        return "{}".format(str(value))

    if isinstance(value, dict):
        if len(value) == 0:
            return "[]"

        output = []
        for key in value.keys():
            subvalue = convert_to_php(value[key], indent + 4)
            output.append((" "*indent) + "'{}' => {},\n".format(key, subvalue))

        return "[\n" + "".join(output) + (" "*(indent - 4)) + "]"

    if isinstance(value, list):
        if len(value) == 0:
            return "[]"

        output = []
        for key in value:
            subvalue = convert_to_php(key, indent + 4)
            output.append((" "*indent) + "{},\n".format(subvalue))

        return "[\n" + "".join(output) + (" "*(indent - 4)) + "]"

    return "'{}'".format(str(value))


if __name__ == '__main__':
    demo = {
        'test': {
            'baa': 'bas',
            'test': {
                'baa': 'bas',
                'test': 'bas',
                'value': True,
                'int': 14,
            },
            'array': [
                'test',
                'baa',
            ]
        }
    }
    print(convert_to_php(demo))
