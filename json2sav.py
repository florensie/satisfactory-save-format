#!/usr/bin/env python3
"""
Converts from the more readable format (.json) back to a Satisfactory save game (.sav)
"""

import struct
import json
import argparse
import pathlib
import sys

parser = argparse.ArgumentParser(
    description='Converts from the more readable format back to a Satisfactory save game')
parser.add_argument('file', metavar='FILE', type=str,
                    help='json file to process')
parser.add_argument('--output', '-o', type=str, help='output file (.sav)')
args = parser.parse_args()

extension = pathlib.Path(args.file).suffix
if extension == '.sav':
    print('error: extension of save file should be .json', file=sys.stderr)
    exit(1)

f = open(args.file, 'r')
save_json = json.loads(f.read())

if args.output is None:
    output_file = pathlib.Path(args.file).stem + '.sav'
else:
    output_file = args.output

output = open(output_file, 'wb')

buffers = []


def write(bytes, count=True):
    if len(buffers) == 0:
        output.write(bytes)
    else:
        buffers[len(buffers) - 1]['buffer'].append(bytes)
        if count:
            buffers[len(buffers) - 1]['length'] += len(bytes)


def add_buffer():
    """
    pushes a new buffer to the stack, so that the length of the following content can be written before the content
    """
    buffers.append({'buffer': [], 'length': 0})


def end_buffer_and_write_size():
    """
    ends the top buffer and writes it's context prefixed by the length (possibly into another buffer)
    """
    buffer = buffers[len(buffers) - 1]
    buffers.remove(buffer)
    # writeInt(26214) # TODO length
    write_int(buffer['length'])
    for b in buffer['buffer']:
        write(b)
    return buffer['length']


def assert_fail(message):
    print('failed: ' + message)
    input()
    assert False


def write_int(value, count=True):
    write(struct.pack('i', value), count)


def write_float(value):
    write(struct.pack('f', value))


def write_long(value):
    write(struct.pack('l', value))


def write_byte(value, count=True):
    write(struct.pack('b', value), count)


def write_length_prefixed_string(value, count=True):
    if len(value) == 0:
        write_int(0, count)
        return
    write_int(len(value) + 1, count)
    for i in value:
        write(struct.pack('b', ord(i)), count)
    write(b'\x00', count)


def write_hex(value, count=True):
    write(bytearray.fromhex(value), count)


# Header
write_int(save_json['save_header_type'])
write_int(save_json['save_version'])
write_int(save_json['build_version'])
write_length_prefixed_string(save_json['map_name'])
write_length_prefixed_string(save_json['map_options'])
write_length_prefixed_string(save_json['session_name'])
write_int(save_json['play_duration_seconds'])
write_long(save_json['save_date_time'])
write_byte(save_json['session_visibility'])

write_int(len(save_json['objects']))


def write_actor(obj):
    write_length_prefixed_string(obj['class_name'])
    write_length_prefixed_string(obj['level_name'])
    write_length_prefixed_string(obj['path_name'])
    write_int(obj['need_transform'])
    write_float(obj['transform']['rotation'][0])
    write_float(obj['transform']['rotation'][1])
    write_float(obj['transform']['rotation'][2])
    write_float(obj['transform']['rotation'][3])
    write_float(obj['transform']['translation'][0])
    write_float(obj['transform']['translation'][1])
    write_float(obj['transform']['translation'][2])
    write_float(obj['transform']['scale3d'][0])
    write_float(obj['transform']['scale3d'][1])
    write_float(obj['transform']['scale3d'][2])
    write_int(obj['was_placed_in_level'])


def write_object(obj):
    write_length_prefixed_string(obj['class_name'])
    write_length_prefixed_string(obj['level_name'])
    write_length_prefixed_string(obj['path_name'])
    write_length_prefixed_string(obj['outer_path_name'])


for obj in save_json['objects']:
    write_int(obj['type'])
    if obj['type'] == 1:
        write_actor(obj)
    elif obj['type'] == 0:
        write_object(obj)
    else:
        assert_fail('unknown type ' + str(type))

write_int(len(save_json['objects']))


def write_property(property):
    write_length_prefixed_string(property['name'])
    type = property['type']
    write_length_prefixed_string(type)
    add_buffer()
    write_int(0, count=False)
    if type == 'IntProperty':
        write_byte(0, count=False)
        write_int(property['value'])
    elif type == 'BoolProperty':
        write_byte(property['value'], count=False)
        write_byte(0, count=False)
    elif type == 'FloatProperty':
        write_byte(0, count=False)
        write_float(property['value'])
    elif type == 'StrProperty':
        write_byte(0, count=False)
        write_length_prefixed_string(property['value'])
    elif type == 'NameProperty':
        write_byte(0, count=False)
        write_length_prefixed_string(property['value'])
    elif type == 'TextProperty':
        write_byte(0, count=False)
        write_hex(property['textUnknown'])
        write_length_prefixed_string(property['value'])
    elif type == 'ByteProperty':  # TODO

        write_length_prefixed_string(property['value']['unk1'], count=False)
        if property['value']['unk1'] == 'EGamePhase':
            write_byte(0, count=False)
            write_length_prefixed_string(property['value']['unk2'])
        else:
            write_byte(0, count=False)
            write_byte(property['value']['unk2'])
    elif type == 'EnumProperty':
        write_length_prefixed_string(property['value']['enum'], count=False)
        write_byte(0, count=False)
        write_length_prefixed_string(property['value']['value'])
    elif type == 'ObjectProperty':
        write_byte(0, count=False)
        write_length_prefixed_string(property['value']['level_name'])
        write_length_prefixed_string(property['value']['path_name'])

    elif type == 'StructProperty':
        write_length_prefixed_string(property['value']['type'], count=False)
        write_hex(property['structUnknown'], count=False)

        type = property['value']['type']
        if type == 'Vector' or type == 'Rotator':
            write_float(property['value']['x'])
            write_float(property['value']['y'])
            write_float(property['value']['z'])
        elif type == 'Box':
            write_float(property['value']['min'][0])
            write_float(property['value']['min'][1])
            write_float(property['value']['min'][2])
            write_float(property['value']['max'][0])
            write_float(property['value']['max'][1])
            write_float(property['value']['max'][2])
            write_byte(property['value']['is_valid'])
        elif type == 'LinearColor':
            write_float(property['value']['r'])
            write_float(property['value']['g'])
            write_float(property['value']['b'])
            write_float(property['value']['a'])
        elif type == 'Transform':
            for prop in property['value']['properties']:
                write_property(prop)
            write_none()
        elif type == 'Quat':
            write_float(property['value']['a'])
            write_float(property['value']['b'])
            write_float(property['value']['c'])
            write_float(property['value']['d'])
        elif type == 'RemovedInstanceArray' or type == 'InventoryStack':
            for prop in property['value']['properties']:
                write_property(prop)
            write_none()
        elif type == 'InventoryItem':
            write_length_prefixed_string(property['value']['unk1'], count=False)
            write_length_prefixed_string(property['value']['itemName'])
            write_length_prefixed_string(property['value']['level_name'])
            write_length_prefixed_string(property['value']['path_name'])
            oldval = buffers[len(buffers) - 1]['length']
            write_property(property['value']['properties'][0])
            # Dirty hack to make in this one case the inner property only take up 4 bytes
            buffers[len(buffers) - 1]['length'] = oldval + 4

    elif type == 'ArrayProperty':
        item_type = property['value']['type']
        write_length_prefixed_string(item_type, count=False)
        write_byte(0, count=False)
        write_int(len(property['value']['values']))
        if item_type == 'IntProperty':
            for obj in property['value']['values']:
                write_int(obj)
        elif item_type == 'ObjectProperty':
            for obj in property['value']['values']:
                write_length_prefixed_string(obj['level_name'])
                write_length_prefixed_string(obj['path_name'])
        elif item_type == 'StructProperty':
            write_length_prefixed_string(property['struct_name'])
            write_length_prefixed_string(property['struct_type'])
            add_buffer()
            write_int(0, count=False)
            write_length_prefixed_string(property['structInnerType'], count=False)
            write_hex(property['structUnknown'], count=False)
            for obj in property['value']['values']:
                for prop in obj['properties']:
                    write_property(prop)
                write_none()
            struct_length = end_buffer_and_write_size()
            if struct_length != property['_structLength']:
                print('struct: ' + str(struct_length) +
                      '/' + str(property['_structLength']))
                print(json.dumps(property, indent=4))
    elif type == 'MapProperty':
        write_length_prefixed_string(property['value']['name'], count=False)
        write_length_prefixed_string(property['value']['type'], count=False)
        write_byte(0, count=False)
        write_int(0)  # for some reason this counts towards the length

        write_int(len(property['value']['values']))
        for key, value in property['value']['values'].items():
            write_int(int(key))
            for prop in value:
                write_property(prop)
            write_none()
    length = end_buffer_and_write_size()
    if length != property['_length']:
        print(str(length) + '/' + str(property['_length']))
        print(json.dumps(property, indent=4))


def write_none():
    write_length_prefixed_string('None')


def write_entity(with_names, obj):
    add_buffer()  # size will be written at this place later
    if with_names:
        write_length_prefixed_string(obj['level_name'])
        write_length_prefixed_string(obj['path_name'])
        write_int(len(obj['children']))
        for child in obj['children']:
            write_length_prefixed_string(child['level_name'])
            write_length_prefixed_string(child['path_name'])

    for property in obj['properties']:
        write_property(property)
    write_none()

    write_hex(obj['missing'])
    end_buffer_and_write_size()


for obj in save_json['objects']:
    if obj['type'] == 1:
        write_entity(True, obj['entity'])
    elif obj['type'] == 0:
        write_entity(False, obj['entity'])

write_hex(save_json['missing'])
