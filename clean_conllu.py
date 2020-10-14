#! /usr/bin/env python3

import sys

if len(sys.argv) < 2:
	print("Use \'-h\' or \'--help\' to see script's purpose.\n"
	      "Give the file name(s) as the parameter(s) otherwise.")
	exit(1)

if sys.argv[1] == "-h" or sys.argv[1] == "--help":
	print("This script is to clean the conllu files of the creeping numbers in the CONLLU format for upos column")
	exit(1)

for i in sys.argv[1:]:
	with open(i, "r", encoding="utf-8") as infile:
		count = 0
		contents = infile.readlines()
		output = []
		for lines in contents:
			if lines != "\n":
				if lines[0] != "#":
					ID, form, lemma, upos, xpos, feats, head, deprel, deps, misc = lines.split("\t")
					if "*" in upos:
						upos = upos.split("*")[1]
						count += 1
					line = ID + "\t" + form + "\t" + lemma + "\t" + upos + "\t" + xpos + "\t" + feats + "\t" + head + "\t" + deprel + "\t" + deps + "\t" + misc
					output.append(line)
				else:
					output.append(lines)
			else:
				output.append(lines)
	print(i + "\t:\t" + str(count))
	
	if count != 0 :
		with open(i+"_final", "w", encoding="utf-8") as outfile:
			for lines in output:
				outfile.write(lines)
