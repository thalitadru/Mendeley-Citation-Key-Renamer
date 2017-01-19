=============================
Mendeley-Citation-Key-Renamer
=============================

Automatically renames citation keys for `Mendeley <http://www.mendeley.com/>`_
reference manager. Default setting will automatically generate citation keys by ``AuthorYearVeryShortTitle`` format. For example, for the following citation:

   Porter, R. H. (1981). A study of cartel stability : the Joint Executive
   Committee , 1880-1886. Bell Journal of Economics, (November), 1880–1886.

it will generate the following citation keys::

   Porter1981study

and update the sqlite database for Mendeley.

You can opt to include some other info by giving flags in the commandline (help under construction!).
The --jounal flag will append a journal abbreviation to the key, using pre-defined rules to generate Journal abbreviation.

Basic Usage
===========
* To use, with Mendeley closed, run it with ``python``::
   .. code-block:: python
       python /path/to/mendeley-rename-citation-key.py --mendeley_db '<youremail>@www.mendeley.com.sqlite' [options]


* ``python /path/to/mendeley-rename-citation-key.py -h`` to see available options


* If you dont inform your --mendeley_path to your sqlite database, it will default to /home/<username>/.local/share/data/Mendeley Ltd./Mendeley Desktop/


* For --journal option: You can add more words by adding them to the ``abbr_rule`` dict

Installation
============

Dependencies
------------

* `APSW <http://rogerbinns.github.io/apsw/download.html>`_
* Unidecode

Download
--------

.. code-block:: sh

    git clone https://github.com/thalitadru/Mendeley-Citation-Key-Renamer.git

Credits
=======
Adapted from https://github.com/joonro/Mendeley-Citation-Key-Renamer.git

