#!/usr/bin/env python2

import os
import sys
import re

SPECIAL_SUFFIX1 = "GIT_INDEX_UNMERGED_TO_REGULAR_CODEC"
SPECIAL_SUFFIX2 = "GIT_INDEX_UNMERGED_CHECKOUT"

def update_index(updates):
    p = os.popen('git update-index --index-info', 'w')
    data = '\n'.join(updates)
    p.write(data)
    r = p.close()
    if r != None:
        print >>sys.stderr, "git-update-index failed"
        sys.exit(r)

def add(lst):
    params = ['git', 'add', '--'] + list(lst)
    r = os.spawnvp(os.P_WAIT, 'git', params)
    if r != 0:
        print >>sys.stderr, "git-add failed (%d)" % (r, )
        sys.exit(r)

def remove(lst):
    params = ['git', 'rm', '-f', '--'] + list(lst)
    r = os.spawnvp(os.P_WAIT, 'git', params)
    if r != 0:
        print >>sys.stderr, "git-add failed (%d)" % (r, )
        sys.exit(r)

def checkout(files, params=None):
    if not params:
        params = []
    else:
        params = params
    params = ['git', 'checkout'] + params + ['--'] + list(files)
    print params
    r = os.spawnvp(os.P_WAIT, 'git', params)
    if r != 0:
        print >>sys.stderr, "git-checkout failed (%d)" % (r, )
        sys.exit(r)

def encode():
    """Turn the unmerged paths, if exist, to a commit"""
    updates = []
    unmerged_filenames = set({})
    unmerged_bogus_filenames = set()

    for line in os.popen('git ls-files --unmerged').read().splitlines():
        meta, filename = line.split('\t')
        mode, sha1hash, stage = meta.split(' ')
        if stage != "0":
            unmerged_filenames.add(filename)
        bogus_filename = filename + ".%s.%s" % (stage, SPECIAL_SUFFIX1)
        unmerged_bogus_filenames.add(bogus_filename)
        updates += ["%s %s 0\t%s" % (mode, sha1hash, bogus_filename)]

    if not updates:
        return

    update_index(updates)
    add(unmerged_filenames)
    checkout(unmerged_bogus_filenames)

    params = ['git', 'commit', '-m', "TEMP-COMMIT: unmerged",
              '--'] + (list(unmerged_bogus_filenames) +
                           list(unmerged_filenames))
    r = os.spawnvp(os.P_WAIT, 'git', params)
    if r != 0:
        print >>sys.stderr, "git-commit failed (%d)" % (r, )
        sys.exit(r)

def decode():
    """Turn a special 'unmerged paths' commit back to unmerged files in index"""
    rev = os.popen('git rev-parse HEAD').read().strip()

    cmd = os.popen('git show HEAD --format="%s" -s').read().strip()
    if cmd != "TEMP-COMMIT: unmerged":
        return

    params = ['git', 'reset', '--soft' ,'HEAD^']
    r = os.spawnvp(os.P_WAIT, 'git', params)
    if r != 0:
        print >>sys.stderr, "git-reset failed (%d)" % (r, )
        sys.exit(r)

    r = re.compile("(.*)[.]([0-9]+)[.]" + SPECIAL_SUFFIX1 + '$')
    lines = os.popen('git ls-files --stage').read().splitlines()
    unmerged_paths = set()
    removals = set()
    updates = []
    for line in lines:
        meta, filename = line.split('\t')
        mode, sha1hash, _ = meta.split(' ')
        m = r.match(filename)
        if not m:
            continue

        removals.add(filename)
        filename, stage = m.groups(0)
        updates += ["%s %s %s\t%s" % (mode, sha1hash, stage, filename)]
        unmerged_paths.add(filename)

    checkouts = []
    for line in lines:
        meta, filename = line.split('\t')
        mode, sha1hash, stage = meta.split(' ')
        if filename in unmerged_paths:
            checkouts += [filename]
            os.rename(filename, filename + SPECIAL_SUFFIX2)
            removals.add(filename)

    remove(removals)
    update_index(updates)
    for filename in checkouts:
        os.rename(filename + SPECIAL_SUFFIX2, filename)

def main():
    if sys.argv[1:] == ["encode"]:
        encode()
    elif sys.argv[1:] == ["decode"]:
        decode()
    else:
        pass

if __name__ == '__main__':
    main()
