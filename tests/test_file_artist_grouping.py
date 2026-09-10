from scripts.regroup_file_artists import artist_tags,union_groups,reserved_groups


def test_no_artist_guessing_and_no_generic_artist_union():
    assert artist_tags(None)==[]
    assert artist_tags(['Unknown','Various Artists','Actual Artist'])==['Actual Artist']
    assert artist_tags('Artist A / accompanist')==['Artist A / accompanist']


def test_file_artist_connects_concerts_and_existing_known_artist():
    rows=[dict(track='a',group='one'),dict(track='b',group='two'),
          dict(track='c',group='three',artist='Artist A'),dict(track='d',group='four')]
    before=[dict(r) for r in rows]
    groups=union_groups(rows,{'a':['Artist A'],'b':['Artist A']})
    assert groups['a']==groups['b']==groups['c'] and groups['d']!=groups['a']
    assert rows==before


def test_reserved_artist_excludes_whole_connected_group_not_just_matched_track():
    rows=[dict(track='a',group='one'),dict(track='b',group='one'),dict(track='c',group='two')]
    tags={'a':['Reserved Artist']};groups=union_groups(rows,tags)
    denied=reserved_groups(rows,tags,groups,{'reservedartist'})
    assert groups['a'] in denied and groups['b'] in denied and groups['c'] not in denied
