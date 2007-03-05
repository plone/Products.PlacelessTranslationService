PlacelessTranslationService

   Copyright (C) 2001-2007 Lalo Martins <lalo@laranja.org>,
                 Zope Corporation and Contributors

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 2 of the License, or
   (at your option) any later version.

   See license.txt for more details.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307, USA

What is PlacelessTranslationService?

  PTS is a way of internationalizing (i18n'ing) and localizing (l10n'ing)
  software for Zope 2.
  It's based on the files supported by the GNU gettext set of
  utilities. A good source of information and background reading is
  the gettext documentation:
  
  http://www.gnu.org/software/gettext/manual/

Installation

  PTS is installed as a normal Zope product. This is usually done by unpacking
  the distribution into the Products directory of your INSTANCE_HOME
  and restarting Zope. More information can be found in the Zope Book:

  http://zope.org/Documentation/Books/ZopeBook/2_6Edition/MaintainingZope.stx

Using PlacelessTranslationService

  PTS is used in the following steps:

  1. i18n your software

  2. Prepare a translation template

  3. Prepare translations of the template

  4. Install translations

  Each of these is explained below.

1. Internationalizing Your Software

  A good overview of this can be found at:
  http://www.upfrontsystems.co.za/Members/jean/mysite-i18n

2. Preparing a Translation Template

  A translation template is an empty Portable Object file as defined
  by the gettext standard with a special header block. 

  The PO format is described in detail here:

  http://www.gnu.org/software/gettext/manual/html_node/gettext_9.html#SEC9

  The header block is fairly self explanatory and can be seen in the
  sample.pot file included in this directory. All phrases in capitals,
  the language code, language name and (optionally) the content type
  and preferred encodings should be replaced with their correct
  values.

  There are several ways to prepare a PO template:

  -- By hand:
  
     This can be done by copying the blank.pot included in this
     directory, replacing the sample values as described above and and
     then manually adding msgid and empty msgstr pairs for each of the
     msgid's used in your software.

  -- Using i18ndude:

     i18ndude is a tool that is useful when all your software is in
     the form of ZPT's that are stored in files on the filesystem.

     It can be downloaded from:

     http://plone.org/products/i18ndude

3. Prepare Translations of the Template

   Preferably, find a translation company that can handle the gettext
   standards and send them your .pot file. They should send back .po
   files for the languages you require.

   If you're doing it yourself, copy the .pot file to a file on the
   name of the language you're translating to and with a .po
   extension. Then go through that file and fill in the msgstr
   sections. Finally, update all the metadata fields at the top of the
   file so they are correct for the translation you have just
   completed.

   At this point, you should have a .pot file and a collection of .po
   files.

4. Install Translations

   PTS will look in folders called 'i18n' for .po files to use as
   translations. These 'i18n' folders will be searched if they are in
   the INSTANCE_HOME or in the directories of any of the Products you
   have installed.

   Copy your .po files to a 'i18n' folder of your choice in one of
   these locations.

   Once that's done, restart Zope.
