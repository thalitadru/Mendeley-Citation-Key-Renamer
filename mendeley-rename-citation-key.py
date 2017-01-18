# This Python file uses the following encoding: utf-8
import os
import apsw
import re
import string

from unidecode import unidecode
from pprint import pprint


MAX_AUTH = 1
ETAL = False

def get_first_word(title):
    # lista igual a do JabRef https://github.com/JabRef/jabref/blob/master/src/main/java/net/sf/jabref/logic/formatter/casechanger/Word.java
    eliminate = set([
        # articles
        "a", "an", "the", 
        # prepositions
        "above", "about", "across", "against", "along", "among", "around", "at", "before", "behind", "below", "beneath", "beside", "between", "beyond", "by", "down", "during", "except", "for", "from", "in", "inside", "into", "like", "near", "of", "off", "on", "onto", "since", "to", "toward", "through", "under", "until", "up", "upon", "with", "within", "without", 
        # conjunctions
        "and", "but", "for", "nor", "or", "so", "yet"])
    for word in title.replace('-',' ').replace(':','').replace(',','').replace('{','').replace('}', '').split():
        if word.lower() not in eliminate:
            break
    return word


def regexp(expr, item):
    reg = re.compile(expr)
    return reg.search(item) is not None

unicode_rule = {'. ': '-',
                ' ': '-',
                '.': '',
                "'": '',
                u'å': 'a',
                u'ä': 'a',
                u'é': 'e',
                u'è': 'e',
                u'í': 'i',
                u'ö': 'o',
                u'Ö': 'o',
                u'ø': 'o',
                u'ç': 'c',
                u'ü': 'u',
                u'\u2026': '...',
                }

def remove_unicode(arg):
    return unidecode(arg)

if __name__ == '__main__':
    '''
    change Mendeley citation key to author-author-year-journalabbr format
    '''
    sqlite = 'thalitafdrumond@gmail.com@www.mendeley.com.sqlite'  # change

    if os.name == 'nt':
        path_db = r'\Users\thalita\AppData\Local\Mendeley Ltd\Mendeley Desktop\{}'.format(sqlite)
    else:
        path_db = r'/home/thalita/.local/share/data/Mendeley Ltd./Mendeley Desktop/{}'.format(sqlite)

    con = apsw.Connection(path_db)

    con.createscalarfunction("REGEXP", regexp)

    cur = con.cursor()


    cur.execute("SELECT documentId FROM DocumentFolders WHERE (folderId=1 OR folderId=2)")
    documentids = cur.fetchall()[:]

    modified = []  # list of modified citations
    errors = []  # list of citations with errors

    for i, k in enumerate(documentids):
        docid = k[0]
        cur.execute(("SELECT Publication FROM Documents WHERE "
                     "id='{}'").format(docid))

        publication = cur.fetchall()[:][0][0]

        if publication:
            # get the journal abbr
            exception = False
            key_publication = ''
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

        cur.execute(("SELECT lastName FROM DocumentContributors WHERE "
                     "documentID='{}'").format(docid))

        lastnames = cur.fetchall()[:]

        key_author = ''
        for j, lastname in enumerate(lastnames):
            if j == MAX_AUTH:
                key_author += (' ' + 'et-al') * ETAL
                break
            else:
                key_author += ' ' * bool(j) + lastname[0]
        
        key_author = key_author.strip().title()

        key_author = remove_unicode(key_author)
        key_publication = remove_unicode(key_publication)

        cur.execute(("SELECT year FROM Documents WHERE "
                     "id='{}'").format(docid))

        year = cur.fetchall()[:][0][0]

        cur.execute(("SELECT Title FROM Documents WHERE "
                     "id='{}'").format(docid))

        title = cur.fetchall()[:][0][0]
        veryshorttitle = remove_unicode(get_first_word(title))
        
        # citationkey = '{}_{}_{}'.format(key_author, year, key_publication)
        citationkey = '{}{}{}'.format(key_author, year,veryshorttitle) # Thalita
        citationkey = citationkey.replace('None','')
        
        cur.execute(("SELECT citationKey FROM Documents WHERE "
                     "id='{}'").format(docid))

        citationkey_old = cur.fetchall()[:][0][0]

        if citationkey != citationkey_old:
            if not 'test-run':
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
 
    from pprint import pprint
    pprint(modified)
    pprint(errors)
    pprint(duplicates)

