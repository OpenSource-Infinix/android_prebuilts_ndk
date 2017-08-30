#!/usr/bin/env python
#
# Copyright 2015 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os


def local_path(path):
    return os.path.normpath(os.path.join(os.path.dirname(__file__), path))


def find(path, names):
    found = []
    for root, _, files in os.walk(path):
        for file_name in sorted(files):
            if file_name in names:
                abspath = os.path.abspath(os.path.join(root, file_name))
                rel_to_root = abspath.replace(os.path.abspath(path), '')
                found.append(rel_to_root[1:])  # strip leading /
    return found


def sdk_version_from_path(path):
    return int(path.split('/')[0].split('-')[1])


def sdk_versions():
    versions = []
    for sdk in os.listdir(local_path('current/platforms')):
        if sdk.startswith('android-'):
            versions.append(sdk_version_from_path(sdk))
    return sorted(versions)


def gen_defaults():
    defaults = []
    for sdk in sdk_versions():
        default = []
        arch_flags = []

        for arch in ['arm', 'arm64', 'mips', 'mips64', 'x86', 'x86_64']:
            arch_path = local_path(
                'current/platforms/android-{sdk}/arch-{arch}'.format(sdk=sdk, arch=arch))
            if not os.path.exists(arch_path):
                arch_flags.append(
                    '        {arch}: {{ enabled: false, }},'.format(arch=arch))

        default.append('cc_defaults {{\n'
                       '    name: "ndk_{version}_defaults",'.format(version=sdk))
        if len(arch_flags) > 0:
            default.append('    arch: {{\n{arch_flags}\n'
                           '    }},'.format(arch_flags='\n'.join(arch_flags)))
        default.append('}')
        defaults.append('\n'.join(default))
    return defaults


def get_prebuilts(names):
    prebuilts_path = local_path('current/platforms')
    prebuilts = find(prebuilts_path, names)
    prebuilts = [p for p in prebuilts if 'arch-arm/' in p]
    prebuilts.sort(key=sdk_version_from_path)
    return prebuilts


def gen_lib_prebuilt(prebuilt, name, version):
    platform = os.path.join('current', 'platforms',
                            prebuilt.partition('/')[0])
    includes = os.path.join(platform, 'arch-{}/usr/include')
    arch_flags = []
    for arch in ['arm', 'arm64', 'mips', 'mips64', 'x86', 'x86_64']:
        inc = includes.format(arch)
        if os.path.exists(inc):
            arch_flags.append(
                '        {arch}: {{\n'
                '            export_include_dirs: ["{includes}"],\n'
                '        }},'.format(arch=arch, includes=inc))
    return ('ndk_prebuilt_library {{\n'
            '    name: "ndk_{name}.{version}",\n'
            '    defaults: ["ndk_{version}_defaults"],\n'
            '    sdk_version: "{version}",\n'
            '    arch: {{\n{arch_flags}\n'
            '    }},\n'
            '}}'.format(name=name, version=version,
                        arch_flags='\n'.join(arch_flags)))


def gen_crt_prebuilt(_, name, version):
    return ('ndk_prebuilt_object {{\n'
            '    name: "ndk_{name}.{version}",\n'
            '    defaults: ["ndk_{version}_defaults"],\n'
            '    sdk_version: "{version}",\n'
            '}}'.format(name=name, version=version))


def gen_prebuilts(fn, names):
    prebuilts = []
    for prebuilt in get_prebuilts(names):
        name = os.path.splitext(os.path.basename(prebuilt))[0]
        version = sdk_version_from_path(prebuilt)
        prebuilts.append(fn(prebuilt, name, version))
    return prebuilts


def main():
    blueprints = gen_defaults()
    blueprints.extend(gen_prebuilts(gen_lib_prebuilt, ('libc.so', 'libm.so')))
    blueprints.extend(gen_prebuilts(gen_crt_prebuilt, (
        'crtbegin_so.o',
        'crtend_so.o',
        'crtbegin_dynamic.o',
        'crtbegin_static.o',
        'crtend_android.o')))

    with open(local_path('Android.bp'), 'w') as f:
        f.write('// THIS FILE IS AUTOGENERATED BY gen-blueprints.py\n')
        f.write('// DO NOT EDIT\n')
        f.write('\n')
        f.write('\n\n'.join(blueprints))
        f.write('\n\n')
        f.write('build = ["stl.bp"]\n')


if __name__ == '__main__':
    main()
