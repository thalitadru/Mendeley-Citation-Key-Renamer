#! /bin/python
# This Python file uses the following encoding: utf-8
import os
import apsw
import re
import string
import argparse
from collections import defaultdict
from abbr_rule import abbr_rule
from unidecode import unidecode
from pprint import pprint
import getpass


def get_first_word(title):
    # Stop words list from JabRef https://github.com/JabRef/jabref/blob/master/src/main/java/net/sf/jabref/logic/formatter/casechanger/Word.java
    stop_words = set([
        # articles
        "a", "an", "the",
        # Personal: french and portuguese articles
        "la","le","l", "o","um","uma","un","une",
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
             u"’": " "}
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
                        default=None)
    parser.add_argument('--mendeley_path', default=None)
    parser.add_argument('--max_authors', default=1)
    parser.add_argument('--et_al', action="store_true")
    parser.add_argument('-s','--separator', default='')
    parser.add_argument('-v','--veryshorttitle', action="store_true")
    parser.add_argument('-j','--journal', action="store_true")
    parser.add_argument('-t','--test_run', action="store_true")
    parser.add_argument('-f','--folder', action="append")
    args = parser.parse_args()

    path_db = args.mendeley_path
    if args.mendeley_path is None:
        user = getpass.getuser()
        path_db = r'/home/{}/.local/share/data/Mendeley Ltd./Mendeley Desktop/'.format(user)
        print("Using default DB path {}".format(path_db))

    sqlite = args.mendeley_db
    if sqlite is None:
        sqlite = [f for f in os.listdir(path_db)
                  if f.endswith("@www.mendeley.com.sqlite")][0]
        print("Using default DB file {}".format(sqlite))

    ETAL = args.et_al
    MAX_AUTH = int(args.max_authors)

    with apsw.Connection(path_db + sqlite) as con:

        con.createscalarfunction("REGEXP", regexp)

        cur = con.cursor()

        folders = args.folder
        if len(args.folder) is 0:
            result = cur.execute("SELECT name FROM Folders").fetchall()
            folders = [f for f,_ in result]
        folders_query = " OR ".join(["Folders.name=\"{}\"".format(f)
                                   for f in folders])


        cur.execute("SELECT documentId FROM DocumentFolders INNER JOIN Folders ON DocumentFolders.folderId=Folders.id WHERE {}".format(folders_query))
        documentids = cur.fetchall()[:]

        modified = []  # list of modified citations
        errors = []  # list of citations with errors

        for i, k in enumerate(documentids):
            docid = k[0]
            sep = args.separator
            # journal
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
                    if ETAL:
                        key_author += '-' + 'et-al'
                    break
                else:
                    name = lastname[0].split()[-1]
                    name = name.replace('-','').replace("'",'')
                    name = name.strip().title()
                    key_author += '-' * bool(j) + name

            key_author = remove_unicode(key_author)


            cur.execute(("SELECT year FROM Documents WHERE "
                         "id='{}'").format(docid))

            year = str(cur.fetchall()[:][0][0])

            # veryshorttitle
            if args.veryshorttitle:
                cur.execute(("SELECT Title FROM Documents WHERE "
                             "id='{}'").format(docid))

                title = cur.fetchall()[:][0][0]
                veryshorttitle = remove_unicode(get_first_word(title))

            # compose key according to input args
            citationkey = key_author
            if year != '':
                citationkey += sep + year
            if args.veryshorttitle and veryshorttitle != '':
                citationkey += sep + veryshorttitle
            if args.journal and key_publication != '':
                citationkey += sep + key_publication
            citationkey = citationkey.replace('None'+sep,'')

            # get current citation keys
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
        cur.execute("""
        SELECT Documents.id, citationKey
        FROM Documents
            INNER JOIN (DocumentFolders
                INNER JOIN Folders
                ON DocumentFolders.folderId=Folders.id
            )
            ON Documents.id=DocumentFolders.documentId
        WHERE ({}) AND Documents.deletionPending='false'
        """.format(folders_query))
        ids_dict = dict(cur.fetchall())
        citekeys_dict = defaultdict(list)
        for docid, citekey in ids_dict.iteritems():
            citekeys_dict[citekey].append(docid)

        for citationkey, ids in citekeys_dict.iteritems():
            if len(ids) > 1:
                duplicates.append(citationkey + ' (%d)' % (len(ids)))
                ids.sort()
                for rank, docid in enumerate(ids):
                    if rank > 0 :
                        new_key = citationkey + string.ascii_uppercase[rank-1]
                        duplicates.append(new_key)
                        cur.execute("""
                        UPDATE Documents
                        SET citationKey='{new}'
                        WHERE ID={ID}
                        """.format(new=new_key, ID=docid))

        pprint(modified)
        pprint(errors)
        pprint(duplicates)
