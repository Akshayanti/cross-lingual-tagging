#! /usr/bin/env python3

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--true", type=str, help="Gold Standard Data File, CONLL-U format")
parser.add_argument("--generated", type=str, help="Generated Data File, CONLL-U format")
args = parser.parse_args()


pos = []
with open(args.true, "r") as infile:
	contents = infile.readlines()
	for lines in contents:
		if lines != "\n":
			if lines[0] != "#":
				pos_val = lines.split("\t")[3]
				pos.append(pos_val)
match = 0
total = 0
with open(args.generated, "r") as infile:
	contents = infile.readlines()
	for lines in contents:
		if lines != "\n":
			if lines[0] != "#":
				pos_val = lines.split("\t")[3]
				if pos_val == pos[total]:
					match += 1
				total += 1
print(args.generated + str(match * 100 / total), sep="\t")
