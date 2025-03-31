#!/bin/bash

# Yes, regex matching XML is wrong, acknowledged. ( https://stackoverflow.com/a/1732454 )

curl -s https://fi.wikipedia.org/wiki/Luettelo_Suomen_kuntien_koordinaateista | \
perl -ne 'if ($_ =~ m#id="Entiset#) { exit; }; if ($_ =~ m#;title=([^"]*)".*p">([^<]*).*p">([^<]*)<#) { print "$1,$2,$3\n"; }' | \
perl -ne 's/°[NE]//g; print' | \
perl -ne 's/%C3%B6/o/g; print' | \
perl -ne 's/%C3%A4/a/g; print' | \
perl -ne 's/%C3%A5/a/g; print' | \
perl -ne 's/%C3%84/A/g; print' | \
perl -ne 's/Enontekio/Kilpisjarvi/; print' \
> coordinates.csv
