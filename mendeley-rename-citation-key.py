#! /bin/python
# This Python file uses the following encoding: utf-8
import os
import apsw
import re
import string
import argparse
from abbr_rule import abbr_rule
from unidecode import unidecode
from pprint import pprint
import getpass


def get_first_word(title):
    # Stop words list from JabRef https://github.com/JabRef/jabref/blob/master/src/main/java/net/sf/jabref/logic/formatter/casechanger/Word.java
    stop_words = set([
        # articles
        "a", "an", "the",
        # Personal: french and partuguese articles
        "la","le","l", "o","um","un","une"
        # prepositions
        "above", "about", "across", "against", "along", "among", "around", "at", "before", "behind", "below", "beneath", "beside", "between", "beyond", "by", "down", "during", "except", "for", "from", "in", "inside", "into", "like", "near", "of", "off", "on", "onto", "since", "to", "toward", "through", "under", "until", "up", "upon", "with", "within", "without",
        # conjunctions
        "and", "but", "for", "nor", "or", "so", "yet"])
    signs = {"-": " ",
             ":": " ",
             ",": " ",
             "{": "",
             "}": "",
             "'": " ",
             "’": " "}
    for sign, replacement in signs.items():
        title = title.replace(sign, replacement)
    for word in title.split():
        if word.lower() not in stop_words:
            break
    return word.capitalize()


def regexp(expr, item):
    reg = re.compile(expr)
    return reg.search(item) is not None


def remove_unicode(arg):
    return unidecode(arg)

if __name__ == '__main__':
    '''
    change Mendeley citation key to <author>[<authors>][et_al]<year>[<veryshorttitle><journalabrev>] format
    '''
    parser = argparse.ArgumentParser(
        description='Generate citation keys according to a given format')
    parser.add_argument('--mendeley_db',
        default= 'thalitafdrumond@gmail.com@www.mendeley.com.sqlite')
    parser.add_argument('--mendeley_path', default=None)
    parser.add_argument('--max_authors', default=1)
    parser.add_argument('--et_al', default=False)
    parser.add_argument('--separator', default='')
    parser.add_argument('--veryshorttitle', default=True)
    parser.add_argument('--journal', default=False)
    parser.add_argument('--test_run', default=False)
    args = parser.parse_args()

    sqlite = args.mendeley_db
    ETAL = args.et_al
    MAX_AUTH = args.max_authors

    if args.mendeley_path is None:
        user = getpass.getuser()
        path_db = r'/home/{}/.local/share/data/Mendeley Ltd./Mendeley Desktop/{}'.format(user, sqlite)
    else:
        path_db = args.mendeley_path + sqlite

    con = apsw.Connection(path_db)

    con.createscalarfunction("REGEXP", regexp)

    cur = con.cursor()


    cur.execute("SELECT documentId FROM DocumentFolders WHERE (folderId=1 OR folderId=2)")
    documentids = cur.fetchall()[:]

    modified = []  # list of modified citations
    errors = []  # list of citations with errors

    for i, k in enumerate(documentids):
        docid = k[0]
        sep = args.separator
        if args.journal:
            cur.execute(("SELECT Publication FROM Documents WHERE "
                         "id='{}'").format(docid))

            publication = cur.fetchall()[:][0][0]
            key_publication = ''
            if publication:
                # get the journal abbr
                exception = False
                for j, word in enumerate(publication.split(' ')):
                    word = word.replace('.', '')
                    word = word.replace(',', '')
                    word = word.replace(':', '')
                    try:
                        temp_abbr = abbr_rule[word.lower()]
                    except:

                        print((u'no word: "{}" in {}'
                               '').format(remove_unicode(word),
                                   remove_unicode(publication)))
                        exception = True
                        continue

                    if len(temp_abbr):
                        key_publication += abbr_rule[word.lower()].title() + '_'

                key_publication = key_publication[:-1]

                if exception:
                    continue
            else:
                cur.execute(("SELECT Type FROM Documents WHERE "
                             "id='{}'").format(docid))
                item_type = cur.fetchall()[:][0][0]
                if item_type == "Book":
                    key_publication = "book"
            key_publication = remove_unicode(key_publication)

        # authors
        cur.execute(("SELECT lastName FROM DocumentContributors WHERE "
                     "documentID='{}'").format(docid))

        lastnames = cur.fetchall()[:]

        key_author = ''
        for j, lastname in enumerate(lastnames):
            if j == MAX_AUTH:
                key_author += ('-' + 'et-al') * ETAL
                break
            else:
                name = lastname[0].split()[-1]
                name = name.replace('-','').replace("'",'')
                key_author += '-' * bool(j) + name
        key_author = key_author.strip().title()

        key_author = remove_unicode(key_author)


        cur.execute(("SELECT year FROM Documents WHERE "
                     "id='{}'").format(docid))

        year = cur.fetchall()[:][0][0]

        # veryshorttitle
        if args.veryshorttitle:
            cur.execute(("SELECT Title FROM Documents WHERE "
                         "id='{}'").format(docid))

            title = cur.fetchall()[:][0][0]
            veryshorttitle = remove_unicode(get_first_word(title))


        citationkey = ('{}'+sep+'{}').format(key_author, year)
        if args.veryshorttitle:
            citationkey += sep + veryshorttitle
        if args.journal:
            citationkey += sep + publication
        citationkey = citationkey.replace('None','')

        cur.execute(("SELECT citationKey FROM Documents WHERE "
                     "id='{}'").format(docid))

        citationkey_old = cur.fetchall()[:][0][0]

        if citationkey != citationkey_old:
            if args.test_run:
                if citationkey_old:
                    modified.append(citationkey_old + ' -> ' +  citationkey)
                else:
                    modified.append('" " -> ' +  citationkey)
            else:
                try:
                    cur.execute(("UPDATE Documents SET citationKey="
                        "'{new}' WHERE ID={ID}").format(new=citationkey,
                                                        ID=docid))
                    modified.append(citationkey_old + ' -> ' + citationkey)
                except:
                    errors.append('error: ' + citationkey)

    duplicates = []
    # Thalita: solve duplicates
    # not ready
    cur.execute("SELECT DISTINCT citationKey FROM Documents INNER JOIN DocumentFolders ON Documents.id=DocumentFolders.documentId  WHERE (DocumentFolders.folderId=1 or DocumentFolders.folderId=2) AND Documents.deletionPending='false'")
    citekeys = cur.fetchall()[:]
    citekeys = set([c[0] for c in citekeys])
    for citationkey in citekeys:
        cur.execute(("SELECT id from Documents INNER JOIN DocumentFolders ON Documents.id=DocumentFolders.documentId  WHERE (DocumentFolders.folderId=1 or DocumentFolders.folderId=2) AND Documents.deletionPending='false' AND Documents.citationKey='{}'").format(citationkey))
        ids = [i[0] for i in cur.fetchall()]
        if len(ids) > 1:
            duplicates.append(citationkey + ' (%d)' % (len(ids)))
            ids.sort()
            for rank, docid in enumerate(ids):
                citationkey += string.ascii_lowercase[rank]
                '''
                cur.execute(("UPDATE Documents SET citationKey="
                             "'{new}' WHERE ID={ID}").format(new=citationkey,
                                                             ID=docid))
                '''


    pprint(modified)
    pprint(errors)
    pprint(duplicates)

