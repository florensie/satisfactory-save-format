#!/usr/bin/env python3
"""
Converts Satisfactory save games (.sav) into a Python dict
"""
import struct
import sys


def to_py(file_path):
    f = open(file_path, 'rb')

    # determine the file size so that we can
    f.seek(0, 2)
    file_size = f.tell()
    f.seek(0, 0)

    bytesRead = 0

    def assert_fail(message):
        print('assertion failed: ' + message, file=sys.stderr)
        # show the next bytes to help debugging
        print(read_hex(32))
        input()
        assert False

    def read_int():
        global bytesRead
        bytesRead += 4
        return struct.unpack('i', f.read(4))[0]

    def read_float():
        global bytesRead
        bytesRead += 4
        return struct.unpack('f', f.read(4))[0]

    def read_long():
        global bytesRead
        bytesRead += 8
        return struct.unpack('q', f.read(8))[0]

    def read_byte():
        global bytesRead
        bytesRead += 1
        return struct.unpack('b', f.read(1))[0]

    def assert_null_byte():
        global bytesRead
        bytesRead += 1
        zero = f.read(1)
        if zero != b'\x00':
            assert_fail('not null but ' + str(zero))

    def read_length_prefixed_string():
        """
        Reads a string that is prefixed with its length
        """
        global bytesRead
        length = read_int()
        if length == 0:
            return ''

        chars = f.read(length - 1)
        zero = f.read(1)
        bytesRead += length

        if zero != b'\x00':  # We assume that the last byte of a string is alway \x00
            if length > 100:
                assert_fail('zero is ' + str(zero) + ' in ' + str(chars[0:100]))
            else:
                assert_fail('zero is ' + str(zero) + ' in ' + str(chars))
        return chars.decode('ascii')

    def read_hex(count):
        """
        Reads count bytes and returns their hex form
        """
        global bytesRead
        bytesRead += count

        chars = f.read(count)
        c = 0
        result = ''
        for i in chars:
            result += format(i, '02x') + ' '
            c += 1
            if c % 4 == 0 and c < count - 1:
                result += ' '

        return result

    # Read the file header
    save_header_type = read_int()
    save_version = read_int()  # Save Version
    build_version = read_int()  # BuildVersion

    map_name = read_length_prefixed_string()  # MapName
    map_options = read_length_prefixed_string()  # MapOptions
    session_name = read_length_prefixed_string()  # SessionName
    play_duration_seconds = read_int()  # PlayDurationSeconds

    save_date_time = read_long()  # SaveDateTime
    '''
    to convert this FDateTime to a unix timestamp use:
    saveDateSeconds = save_date_time / 10000000
    # see https://stackoverflow.com/a/1628018
    print(saveDateSeconds-62135596800)
    '''
    session_visibility = read_byte()  # SessionVisibility

    entry_count = read_int()  # total entries
    save_dict = {
        'save_header_type': save_header_type,
        'save_version': save_version,
        'build_version': build_version,
        'map_name': map_name,
        'map_options': map_options,
        'session_name': session_name,
        'play_duration_seconds': play_duration_seconds,
        'save_date_time': save_date_time,
        'session_visibility': session_visibility,
        'objects': []
    }

    def read_actor():
        class_name = read_length_prefixed_string()
        level_name = read_length_prefixed_string()
        path_name = read_length_prefixed_string()
        need_transform = read_int()

        a = read_float()
        b = read_float()
        c = read_float()
        d = read_float()
        x = read_float()
        y = read_float()
        z = read_float()
        sx = read_float()
        sy = read_float()
        sz = read_float()

        was_placed_in_level = read_int()

        return {
            'type': 1,
            'class_name': class_name,
            'level_name': level_name,
            'path_name': path_name,
            'need_transform': need_transform,
            'transform': {
                'rotation': [a, b, c, d],
                'translation': [x, y, z],
                'scale3d': [sx, sy, sz],

            },
            'was_placed_in_level': was_placed_in_level
        }

    def read_object():
        class_name = read_length_prefixed_string()
        level_name = read_length_prefixed_string()
        path_name = read_length_prefixed_string()
        outer_path_name = read_length_prefixed_string()

        return {
            'type': 0,
            'class_name': class_name,
            'level_name': level_name,
            'path_name': path_name,
            'outer_path_name': outer_path_name
        }

    for i in range(0, entry_count):
        type = read_int()
        if type == 1:
            save_dict['objects'].append(read_actor())
        elif type == 0:
            save_dict['objects'].append(read_object())
        else:
            assert_fail('unknown type ' + str(type))

    element_count = read_int()

    # So far these counts have always been the same and
    # the entities seem to belong 1 to 1 to the actors/objects read above
    if element_count != entry_count:
        assert_fail('element_count (' + str(element_count) +
                    ') != entry_count(' + str(entry_count) + ')')

    def read_property(properties):
        name = read_length_prefixed_string()
        if name == 'None':
            return

        prop = read_length_prefixed_string()
        length = read_int()
        zero = read_int()
        if zero != 0:
            print(name + ' ' + prop)
            assert_fail('not null: ' + str(zero))

        property = {
            'name': name,
            'type': prop,
            '_length': length
        }

        if prop == 'IntProperty':
            assert_null_byte()
            property['value'] = read_int()

        elif prop == 'StrProperty':
            assert_null_byte()
            property['value'] = read_length_prefixed_string()

        elif prop == 'StructProperty':
            type = read_length_prefixed_string()

            property['structUnknown'] = read_hex(17)  # TODO

            if type == 'Vector' or type == 'Rotator':
                x = read_float()
                y = read_float()
                z = read_float()
                property['value'] = {
                    'type': type,
                    'x': x,
                    'y': y,
                    'z': z
                }
            elif type == 'Box':
                min_x = read_float()
                min_y = read_float()
                min_z = read_float()
                max_x = read_float()
                max_y = read_float()
                max_z = read_float()
                is_valid = read_byte()
                property['value'] = {
                    'type': type,
                    'min': [min_x, min_y, min_z],
                    'max': [max_x, max_y, max_z],
                    'is_valid': is_valid
                }
            elif type == 'LinearColor':
                r = read_float()
                g = read_float()
                b = read_float()
                a = read_float()
                property['value'] = {
                    'type': type,
                    'r': r,
                    'g': g,
                    'b': b,
                    'a': a
                }
            elif type == 'Transform':
                props = []
                while read_property(props):
                    pass
                property['value'] = {
                    'type': type,
                    'properties': props
                }

            elif type == 'Quat':
                a = read_float()
                b = read_float()
                c = read_float()
                d = read_float()
                property['value'] = {
                    'type': type,
                    'a': a,
                    'b': b,
                    'c': c,
                    'd': d
                }

            elif type == 'RemovedInstanceArray' or type == 'InventoryStack':
                props = []
                while read_property(props):
                    pass
                property['value'] = {
                    'type': type,
                    'properties': props
                }
            elif type == 'InventoryItem':
                unk1 = read_length_prefixed_string()  # TODO
                item_name = read_length_prefixed_string()
                level_name = read_length_prefixed_string()
                path_name = read_length_prefixed_string()

                props = []
                read_property(props)
                # can't consume null here because it is needed by the entaingling struct

                property['value'] = {
                    'type': type,
                    'unk1': unk1,
                    'item_name': item_name,
                    'level_name': level_name,
                    'path_name': path_name,
                    'properties': props
                }
            else:
                assert_fail('Unknown type: ' + type)

        elif prop == 'ArrayProperty':
            item_type = read_length_prefixed_string()
            assert_null_byte()
            count = read_int()
            values = []

            if item_type == 'ObjectProperty':
                for j in range(0, count):
                    values.append({
                        'level_name': read_length_prefixed_string(),
                        'path_name': read_length_prefixed_string()
                    })
            elif item_type == 'StructProperty':
                struct_name = read_length_prefixed_string()
                struct_type = read_length_prefixed_string()
                struct_size = read_int()
                zero = read_int()
                if zero != 0:
                    assert_fail('not zero: ' + str(zero))
                type = read_length_prefixed_string()

                property['struct_name'] = struct_name
                property['struct_type'] = struct_type
                property['structInnerType'] = type

                property['structUnknown'] = read_hex(17)  # TODO what are those?
                property['_structLength'] = struct_size
                for i in range(0, count):
                    props = []
                    while read_property(props):
                        pass
                    values.append({
                        'properties': props
                    })

            elif item_type == 'IntProperty':
                for i in range(0, count):
                    values.append(read_int())
            else:
                assert_fail('unknown item_type ' + item_type)

            property['value'] = {
                'type': item_type,
                'values': values
            }
        elif prop == 'ObjectProperty':
            assert_null_byte()
            property['value'] = {
                'level_name': read_length_prefixed_string(),
                'path_name': read_length_prefixed_string()
            }
        elif prop == 'BoolProperty':
            property['value'] = read_byte()
            assert_null_byte()
        elif prop == 'FloatProperty':  # TimeStamps that are FloatProperties are negative to
            # the current time in seconds?
            assert_null_byte()
            property['value'] = read_float()
        elif prop == 'EnumProperty':
            enum_name = read_length_prefixed_string()
            assert_null_byte()
            value_name = read_length_prefixed_string()
            property['value'] = {
                'enum': enum_name,
                'value': value_name,
            }
        elif prop == 'NameProperty':
            assert_null_byte()
            property['value'] = read_length_prefixed_string()
        elif prop == 'MapProperty':
            name = read_length_prefixed_string()
            value_type = read_length_prefixed_string()
            for i in range(0, 5):
                assert_null_byte()
            count = read_int()
            values = {
            }
            for i in range(0, count):
                key = read_int()
                props = []
                while read_property(props):
                    pass
                values[key] = props

            property['value'] = {
                'name': name,
                'type': value_type,
                'values': values
            }
        elif prop == 'ByteProperty':  # TODO

            unk1 = read_length_prefixed_string()  # TODO
            if unk1 == 'None':
                assert_null_byte()
                property['value'] = {
                    'unk1': unk1,
                    'unk2': read_byte()
                }
            else:
                assert_null_byte()
                unk2 = read_length_prefixed_string()  # TODO
                property['value'] = {
                    'unk1': unk1,
                    'unk2': unk2
                }

        elif prop == 'TextProperty':
            assert_null_byte()
            property['textUnknown'] = read_hex(13)  # TODO
            property['value'] = read_length_prefixed_string()
        else:
            assert_fail('Unknown property type: ' + prop)

        properties.append(property)
        return True

    def read_entity(with_names, length):
        global bytesRead
        bytesRead = 0

        entity = {}

        if with_names:
            entity['level_name'] = read_length_prefixed_string()
            entity['path_name'] = read_length_prefixed_string()
            entity['children'] = []

            child_count = read_int()
            if child_count > 0:
                for i in range(0, child_count):
                    level_name = read_length_prefixed_string()
                    path_name = read_length_prefixed_string()
                    entity['children'].append({
                        'level_name': level_name,
                        'path_name': path_name
                    })
        entity['properties'] = []
        while read_property(entity['properties']):
            pass

        # read missing bytes at the end of this entity.
        # maybe we missed something while parsing the properties?
        missing = length - bytesRead
        if missing > 0:
            entity['missing'] = read_hex(missing)
        elif missing < 0:
            assert_fail('negative missing amount: ' + str(missing))

        return entity

    for i in range(0, element_count):
        length = read_int()  # length of this entry
        if save_dict['objects'][i]['type'] == 1:
            save_dict['objects'][i]['entity'] = read_entity(True, length)
        else:
            save_dict['objects'][i]['entity'] = read_entity(False, length)

    # store the remaining bytes as well so that we can recreate the exact same save file
    save_dict['missing'] = read_hex(file_size - f.tell())

    return save_dict
