#! /usr/bin/env python3

import argparse
import pickle
from collections import defaultdict
import random
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", type=str, help="Input File with source data in CONLL-U format, where lemma would be read from", required=True)
parser.add_argument("-l", "--lang_scores", type=str, nargs='+', help="Input file with language scores in TSV format, for weight allocation", required=False)
parser.add_argument("-a", "--alignments", type=str, nargs='+', help="Input file containing the alignments", required=True)
parser.add_argument("-c", "--conllu", type=str, nargs='+', help="CONLLU files for the files in \'--alignments\' switch", required=True)
parser.add_argument("-o", "--output", type=str, help="Output File with source data in CONLL-U format, tokenised. This is where predictions would be written", required=False)
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--pickle", action='store_true', help="Save the pickles for the POS alignments and quit")
group.add_argument("--already_pickled", type=str, nargs='+', help="Load the already pickled values, and continue from there.\n"
																  "First argument should be sentence alignment\n"
																  "Second argument should be word alignment.")
parser.add_argument("-rf", "--random_fill", action='store_true', help="If true, selects one value at random in case of multiple possibilities.\n"
																	  "Else, selects the best POS based on the lemma_based encountering of the tokens. \n"
																	  "Default: False")
parser.add_argument("-f", "--lemma_based_decision", action='store_true',
					help="If true, selects the best POS based on the lemma_based encountering of the tokens for unfilled values, later resorting to form-based POS tags.\n"
						 "Else, selects the best POS based on just the form-based POS tags.\n"
						 "Default: False")
args = parser.parse_args()


# Routine checks with the arguments done here
# calls normalize_scores()
def routine_checks(scores, order):
	if args.lang_scores:
		with open(args.lang_scores[0], "r", encoding="utf-8") as lang_file:
			contents = lang_file.readlines()
			if len(contents) != len(args.alignments):
				print("The number of languages in \'-l (--lang_scores)\' is not equal to number of files in \'-a (--alignments)\'.\n"
					  "Check the files, and try again.")
				exit(1)
			else:
				for lines in contents:
					val = lines.strip("\n").split()
					scores[val[0]] = float(val[1])
					order.append(val[0])
				
				if len(args.lang_scores) > 1:
					import statistics
					for i in range(1, len(args.lang_scores)):
						with open(args.lang_scores[i], "r", encoding="utf-8") as lang_file:
							contents = lang_file.readlines()
							if len(contents) != len(args.alignments):
								print("The number of languages in \'-l (--lang_scores)\' is not equal to number of files in \'-a (--alignments)\'.\n"
									  "Check the files, and try again.")
								exit(1)
							else:
								for lines in contents:
									val = lines.strip("\n").split()
									harmonic_data = [float(val[1]), scores[val[0]]]
									scores[val[0]] = statistics.harmonic_mean(harmonic_data)
				
				scores = normalize_scores(scores)
	
	# Need not check with args.lang_scores.
	# Assign equal weights to all input args.alignments files and normalize them.
	# Store the normalized scores in 'scores' dictionary as before.
	else:
		print("NOTE: \tNo \'-l (--lang_scores)\' argument found.\n"
			  "All files in \'-a (--alignments)\' will have equal weights.")
		for files in args.alignments:
			scores[files.split("/")[1].split("_")[0]] = 1
			order.append(files.split("/")[1].split("_")[0])
		scores = normalize_scores(scores)
	
	# Check if the number of files in args.conllu is same as the number of files in args.alignments.
	# If not, quit with appropriate help message.
	# If yes, check their names.
	if len(args.alignments) == len(args.conllu):
		# store the list of files in args.conllu here, and then check with args.alignments
		vals = []
		for i in args.conllu:
			vals.append(i.split("/")[1].split(".")[0])
		for i in args.alignments:
			files = i.split("/")[1].split("_")[0]
			if files in vals:
				vals.remove(files)
			else:
				print("No alignment file for " + i + " found.\n"
													 "Check the files, and try again.")
				exit(1)
		if len(vals) != 0:
			for i in vals:
				print("No CONLLU file found for language \'" + i + "\'.\n"
																   "Check the files, and try again")
			exit(1)
	else:
		print("Unequal number of files in \'-a (--alignments)\' and \'-c (--conllu)\'.\n"
			  "Check the files, and try again.")
		exit(1)
	
	return scores, order


# Return normalized scores in case of multiple inputs for args.alignments
# called by routine_checks()
def normalize_scores(score_list):
	total = 0
	for i in score_list:
		total += score_list[i]
	for i in score_list:
		score_list[i] /= total
	return score_list


# converts the list of strings to a list of ints
# called by word_alignments()
def align_as_int(align_string):
	vals = []
	ints = align_string.split()
	if len(ints) != 0:
		for i in ints:
			if i != "":
				vals.append(int(i))
	return vals


# Generates alignments at the sentence level, using the alignments file(s)
# Used when generating pickles
def sentence_alignments(alignment_file, fol):
	sentences = dict()
	parallel_data = alignment_file.split("/")[0] + "/" + fol + "-" + alignment_file.split("/")[1].split("_")[0]
	ifile = open(parallel_data, "r", encoding="utf-8")
	parallel_data = ifile.readlines()
	with open(alignment_file, "r", encoding="utf-8") as a_file:
		contents = a_file.readlines()
		for i in range(len(contents)):
			# Get the source sentence from the alignments file
			if i % 3 == 0:
				source_sentence_number = int(contents[i].strip("\n").split("(")[1].split(")")[0]) - 1
				source, target = parallel_data[source_sentence_number].strip("\n").split("\t")
				sentences[source] = target
	ifile.close()
	return sentences


# Returns a list by substituting the items in int_list with the corresponding index of item in phrases
# called by word_alignments()
def replace_tokens(int_list, phrases):
	val = []
	if len(int_list) != 0:
		for i in int_list:
			val.append(phrases[i - 1])
	return val


# Generates alignments at the sentence level, using the alignments file(s)
# calls align_as_int(), replace_tokens()
def word_alignments(alignment_file, folder):
	words_with_source = defaultdict(dict)
	
	parallel_data = alignment_file.split("/")[0] + "/" + folder + "-" + alignment_file.split("/")[1].split("_")[0]
	ifile = open(parallel_data, "r", encoding="utf-8")
	parallel_data = ifile.readlines()
	
	with open(alignment_file, "r", encoding="utf-8") as a_file:
		contents = a_file.readlines()
		source = ""
		phrase = ""
		for i in range(len(contents)):
			if i % 3 == 0:
				words = dict()
				source = ""
				source_sentence_number = int(contents[i].strip("\n").split("(")[1].split(")")[0]) - 1
				source = parallel_data[source_sentence_number].strip("\n").split("\t")[0]
				words.clear()
				phrase = ""
			if i % 3 == 1:
				phrase = contents[i].strip("\n").split()
			if i % 3 == 2:
				tgt_list = []
				tgt_list = contents[i].strip("\n").split("})")
				tgt_list = tgt_list[1:-1]
				for z in tgt_list:
					tgt, align = z.split(" ({ ")
					words[tgt.strip(" ")] = replace_tokens(align_as_int(align), phrase)
				words_with_source[source] = words
	return words_with_source


# find the CONLLU-block that corresponds to the input_str in the contents of the CONLLU file (stored in file_contents)
# called by get_projections()
def find_str(input_str, file_contents):
	contents = file_contents
	val = []
	for i in range(len(contents)):
		lines = contents[i]
		if lines != "\n":
			if lines[:3] == "# t":
				text, string = lines.strip("\n").split("# text = ")
				if string == input_str:
					j = i + 1
					while contents[j] != "\n":
						val.append(contents[j].strip("\n"))
						j += 1
					return val


# replace the contents in original_list variable by a particular field from corresponding sentence stored in conllu_values_list.
# calls return_field_conllu()
# called by get_projections()
def align_POS_from_conllu(conllu_values_list, original_list):
	val = []
	for i in original_list:
		val.append(return_field_conllu(conllu_values_list, "form", i, "upos"))
	return val


# Navigates in the ip_list to check_field_name field (str, case insensitive).
# If the value of the field is same as check_field_value, the value in return_field_name is returned.
# called by align_POS_from_conllu(), get_lemma_based_tags()
def return_field_conllu(ip_list, check_field_name, check_field_value, return_field_name):
	for i in ip_list:
		if i[:2] != "# " and i != "\n":
			fields = ["ID", "FORM", "LEMMA", "UPOS", "XPOS", "FEATS", "HEAD", "DEPREL", "DEPS", "MISC"]
			return_field = 0
			for k in range(len(fields)):
				if return_field_name.upper() == fields[k]:
					return_field = k
			vals = i.split("\t")
			for j in range(len(fields)):
				if check_field_name.upper() == fields[j]:
					if j != 0:
						if vals[j] == check_field_value:
							return vals[return_field]
					else:
						if int(vals[j]) == check_field_value:
							return vals[return_field]
	return check_field_value


# returns all the strings in the input conllu file
# called by combine_projections()
def return_strings():
	val = []
	with open(folder + "/" + folder + ".conllu", "r", encoding="utf-8") as conllu_file:
		contents = conllu_file.readlines()
		for line in contents:
			if line != "\n" and len(line) > 4:
				if line[:3] == "# t":
					val.append(line.strip("\n").split("# text = ")[1])
	return val


# does not affect first argument, modifies the second argument to now contain the projected POS tags, instead of projected tokens
# calls find_str(), align_POS_from_conllu() as defined before
def get_projections(sentence_alignments_dict, word_alignments_dict):
	sentence_dict = sentence_alignments_dict
	word_dict = word_alignments_dict
	for i in range(len(word_dict)):
		with open(folder + "/" + order[i] + ".conllu", "r", encoding="utf-8") as conllu_file:
			file_contents = conllu_file.readlines()
			for source_sent in word_dict[i]:
				structure = find_str(sentence_dict[i][source_sent], file_contents)
				for word in word_dict[i][source_sent]:
					a = align_POS_from_conllu(structure, word_dict[i][source_sent][word])
					word_dict[i][source_sent][word].clear()
					word_dict[i][source_sent][word] = a
	return sentence_dict, word_dict


# calculates the scores for each POS candidate, attaching it as a string with the tag
def set_scores(word_alignment_dict, score_dict, order_dict):
	word_dict = word_alignment_dict
	for i in range(len(word_dict)):
		for sentence in word_dict[i]:
			for words in word_dict[i][sentence]:
				val = word_dict[i][sentence][words]
				new_val = []
				for values in val:
					if values is not None:
						if values != "_":
							new_val.append(str(score_dict[order_dict[i]]) + "*" + values)
				word_dict[i][sentence][words] = new_val
	return word_dict


# combines the score metrics of the same POS tag, to give distinct POS tags, with updated scores.
# called by combine_scores_dict_level()
def combine_scores(POS_list_with_scores):
	POS = dict()
	vals = []
	for values in POS_list_with_scores:
		score, POS_val = float(values.split("*")[0]), values.split("*")[1]
		if POS_val in POS:
			POS[POS_val] += score
		else:
			POS[POS_val] = score
	for POS_values in POS:
		vals.append(str(POS[POS_values]) + "*" + POS_values)
	return vals


# calls combine_scores() as defined above for each list
def combine_scores_dict_level(alignments_dict):
	al = alignments_dict
	for sentences in al:
		for words in al[sentences]:
			al[sentences][words] = combine_scores(al[sentences][words])
	return al


# combines projections from different alignments into one
# calls return_strings()
def combine_projections(word_dict):
	vals = defaultdict(dict)
	for target_sent in return_strings():
		words = dict()
		for word in target_sent.split():
			words[word] = []
			for i in range(len(word_dict)):
				if target_sent in word_dict[i]:
					if word in word_dict[i][target_sent]:
						words[word] += word_dict[i][target_sent][word]
		vals[target_sent] = words
	return vals


# Input: alignment dict, with POS_value of a word in following format:
# [count1*value1, count2*value2, ...]			where counti is float in string, and valuei is pos_value
# calculates the max value of counti, and in case the value is not shared by any other valuei, announces it as clear winner.
# In case of max counti being shared by more than 1 valuei, copies the older list.
# The ambiguity in latter case is resolved later in an another function.
def decide_by_voting(alignments_dict_with_multiple_POS):
	working_dict = alignments_dict_with_multiple_POS
	for sentences in working_dict:
		for words in working_dict[sentences]:
			val = working_dict[sentences][words]
			# if there are more than 1 items present, select a winner
			if len(val) >= 2:
				max = 0
				max_val = ""
				count = 0  # for keeping a tab on maximum values that share the current max_score
				for items in val:
					POS_val = items.split("*")[1]
					POS_score = float(items.split("*")[0])
					if POS_score > max:
						max = POS_score
						max_val = POS_val
						count = 1
					elif POS_score == max:
						count += 1
				# if only 1 pos_tag has max_score
				if count == 1:
					working_dict[sentences][words] = [max_val]
			# else, do nothing
			# if there is just one item beforehand
			elif len(val) == 1:
				working_dict[sentences][words] = [val[0].split("*")[1]]
	return working_dict


# takes in input the dict with alignments decided by voting
# returns a nested defaultdict in format of [words][POS_encountered][count] for each word.
# refreshes our pos_dict
# called by pos_encountered_disambiguation() to perform disambiguation
def pos_encountered(alignments_with_voting):
	POS = defaultdict(dict)
	for sent in alignments_with_voting:
		for words in alignments_with_voting[sent]:
			val = alignments_with_voting[sent][words]
			# the case where the voting has already decided best contender
			if len(val) == 1:
				if words.lower() in POS:
					if val[0] in POS[words.lower()]:
						POS[words.lower()][val[0]] += 1
					else:
						POS[words.lower()][val[0]] = 1
				else:
					POS[words.lower()][val[0]] = 1
	return POS


# takes in input a list of score*pos format
# returns the values with the maximum scores as list
# called by pos_encountered_disambiguation()
def return_maximal(list_of_POS_with_count):
	vals = []
	max = 0
	count = 0
	for i in list_of_POS_with_count:
		score = float(i.split("*")[0])
		POS = i.split("*")[1]
		if score > max:
			count = 1
			vals = [POS]
			max = score
		elif score == max:
			count += 1
			vals.append(POS)
	return vals


# for the token in the dict, selects value with maximum counts
# returns the list of all the elements occuring in majority
# called by pos_encountered_disambiguation()
def remove_ambiguity(token, dict_with_pos):
	max = 0
	count = 0
	vals = []
	for values in dict_with_pos[token]:
		if dict_with_pos[token][values] > max:
			count = 1
			vals = [values]
			max = dict_with_pos[token][values]
		elif dict_with_pos[token][values] == max:
			count += 1
			vals.append(values)
	if count > 1:
		return False, vals
	else:
		return True, vals


# takes in input as the dict generated after voting.
# calls pos_encountered() as defined above
# creates a pos_dict with pos_encountered() + max_scores pos_values for the word
# updates the input by adding all the updated_pos if there is a new clear winner.
# tries to disambiguate the cases where pos_encountered() fails
# calls pos_encountered(), return_maximal() and remove_ambiguity() as defined before.
def pos_encountered_disambiguation(alignments_with_voting):
	pos_dict = pos_encountered(alignments_with_voting)
	
	# update pos_dict by using max_scores from alignments.
	for sent in alignments_with_voting:
		for words in alignments_with_voting[sent]:
			val = alignments_with_voting[sent][words]
			if len(val) >= 2:
				val2 = return_maximal(val)
				for values in val2:
					if values in pos_dict[words.lower()]:
						pos_dict[words.lower()][values] += 1
					else:
						pos_dict[words.lower()][values] = 1
	
	# traverse the alignments again, updating them in case of a new clear winner
	# let it be, if otherwise.
	for sent in alignments_with_voting:
		for words in alignments_with_voting[sent]:
			val = alignments_with_voting[sent][words]
			if len(val) >= 2:
				if remove_ambiguity(words.lower(), pos_dict)[0]:
					alignments_with_voting[sent][words] = remove_ambiguity(words.lower(), pos_dict)[1]
	
	# return updated input, and generated dict, corrected as per updated input
	return alignments_with_voting, pos_encountered(alignments_with_voting)


# get a dict containing all the lemmas as the keys.
# calls return_field_conllu() as defined before
def get_lemma_based_tags(alignments_dict):
	lemma_dict = defaultdict(dict)
	with open(args.input, "r", encoding="utf-8") as infile:
		contents = infile.readlines()
		for lines in return_strings():
			for words in alignments_dict[lines]:
				lemma = return_field_conllu(find_str(lines, contents), "form", words, "lemma").lower()
				if lemma != "_":
					if len(alignments_dict[lines][words]) == 1:
						pos = alignments_dict[lines][words][0]
						if lemma in lemma_dict:
							# if pos has been encountered before
							if pos in lemma_dict[lemma]:
								lemma_dict[lemma][pos] += 1
							# in case of a new pos
							else:
								lemma_dict[lemma].update({pos: 1})
						# if lemma is not in the final dict
						else:
							lemma_dict[lemma] = {pos: 1}
	return lemma_dict


# return the input list by converting it into a string
# adds a seperater between each token, apart from the last one.
# Finally appended by a '\n' at end of the string.
# called by process_output()
def write_as_str(list_item, sep):
	output = ""
	for i in range(len(list_item) - 1):
		output += list_item[i] + sep
	output += list_item[len(list_item) - 1] + "\n"
	return output


# returns the string ready to be written in the file.
# calls write_as_str()
# called by write_output()
def process_output(ip_sentence, token_details, alignments_data, pos_dict):
	new_details = token_details.split("\t")
	token = new_details[1]
	pos = "_"
	
	if "-" in new_details[0]:
		pass
	elif token in alignments_data[ip_sentence]:
		pos = alignments_data[ip_sentence][token]
		
		# blank data
		if len(pos) == 0:
			# occurs in Pos dictionary
			if token.lower() in pos_dict:
				_, vals = remove_ambiguity(token.lower(), pos_dict)
				if _:
					pos = vals[0]
				else:
					pos = random.sample(vals, 1)[0]
			
			# not in POS dictionary
			else:
				pos = "NOUN"
		# non-blank data
		else:
			pos = pos[0]
	
	# not tokenized in this way by our anlaysis
	elif token not in alignments_data[ip_sentence]:
		if " " in token:
			tokens = token.split(" ")
			val = []
			for i in tokens:
				if i in alignments_data[ip_sentence]:
					pos = alignments_data[ip_sentence][i]
					
					if len(pos) == 0:
						if i.lower() in pos_dict:
							_, vals = remove_ambiguity(i.lower(), pos_dict)
							val.append(vals[0])
			if len(val) != 0:
				pos = random.sample(val, 1)[0]
			else:
				pos = "NOUN"
		
		elif token.lower() in pos_dict:
			_, pos = remove_ambiguity(token.lower(), pos_dict)
			if _:
				pos = pos[0]
			else:
				pos = random.sample(pos, 1)[0]
		
		else:
			pos = "NOUN"
	
	new_details[3] = pos
	return write_as_str(new_details, "\t")


# stores all the elements of the output conllu file in a list for direct printing
# contains the final outputs
# calls process_output_token()
def write_output(alignments_data, pos_dict):
	output_list = []
	with open(args.output, "r", encoding="utf-8") as conllu_file:
		contents = conllu_file.readlines()
		for sentences in contents:
			if sentences == "\n":
				output_list.append(sentences)
			elif sentences[0] == "#":
				output_list.append(sentences)
				# extract the conllu block of this sentence, if of form '# text ='
				if sentences[:3] == "# t":
					sent = sentences.split("# text = ")[1].strip("\n")
					conllu_block = find_str(sent, contents)
					for token_details in conllu_block:
						output_list.append(process_output(sent, token_details, alignments_data, pos_dict))
	return output_list


# main function
if __name__ == "__main__":
	# for keeping a track of weights, and the languages
	scores = dict()
	# for keeping a track of current directory
	folder = args.input.split("/")[0]
	# for keeping a track of the input file order
	order = []
	
	scores, order = routine_checks(scores, order)
	alignments_word = []
	alignments_sentence = []
	
	if not args.already_pickled:
		# the values are stored in the order of alignments, and so will be easier to manage.
		for i in args.alignments:
			alignments_sentence.append(sentence_alignments(i, folder))
			alignments_word.append(word_alignments(i, folder))
		
		time_start = datetime.now()
		alignments_sentence, alignments_word = get_projections(alignments_sentence, alignments_word)
		
		if args.pickle:
			pickle.dump(alignments_sentence, open(folder + "/" + "sentence_pickle", "wb"))
			pickle.dump(alignments_word, open(folder + "/" + "word_pickle", "wb"))
			print("Pickles dumped in " + str(datetime.now() - time_start) + "\n\n\n")
			exit(0)
		else:
			pass
	else:
		alignments_sentence = pickle.load(open(folder + "/" + args.already_pickled[0], "rb"))
		alignments_word = pickle.load(open(folder + "/" + args.already_pickled[1], "rb"))
	
	# combine the different alignments from the different sources, and then add the scores.
	alignments = set_scores(alignments_word, scores, order)
	alignments = combine_projections(alignments)
	alignments = combine_scores_dict_level(alignments)
	
	# Now, the alignments are ready in a single defaultdict.
	# First, we vote for the most likely value, and save that, making the internal dict, as a dict of strings (POS).
	# We save that in a different file, since we also need the alignment scores for unpopulated values.
	alignments_final = decide_by_voting(alignments)
	
	# get a nested dict of all the words encountered with the counts of POS encountered in them.
	# However, there are cases when a certain word might have equal number of maximal POS-tags encountered by voting.
	# This needs to be dismbiguated, and is done by the function called here.
	# Still, a few cases remain which will be taken care of next.
	alignments_final, words_and_pos = pos_encountered_disambiguation(alignments_final)
	
	# End of VOTING ALIGNMENT
	# Problems remaining:
	# 1. Some of the words still have no clear-cut winner
	# 2. A lot of the words don't have anything to start with, and need to be tagged from scratch.
	
	# For Problem 1
	# Approach 1:
	# From the most likely_contenders, select one at random and assign that POS tag.
	# Approach 2:
	# Same as in Problem 2
	
	# For Problem 2
	# Approach 1:
	# From the generated POS_list, populate what we can based on if there was an alignment earlier at some other point of time.
	# Approach 2:
	# Use lemmas of individual words, and assign the tag used as per the lemma of the current word.
	# In case there are contenders, select one at random from the contendors.
	
	# We define each of the approaches in 2 different argument switches, and test accuracy with each.
	
	# PROBLEM 1
	
	# fill in the position with one of the random values from a multiple-option list
	if args.random_fill:
		time_start = datetime.now()
		for sentences in alignments_final:
			for words in alignments_final[sentences]:
				val = alignments_final[sentences][words]
				if len(val) >= 2:
					val = return_maximal(val)
					val = random.sample(val, 1)
					alignments_final[sentences][words] = val
		# refresh the POS dict
		words_and_pos = pos_encountered(alignments_final)
		print("Time for random_selection based filling (part 1): " + str(datetime.now() - time_start))
	
	
	else:
		time_start = datetime.now()
		lemma_tags = get_lemma_based_tags(alignments_final)
		infile = open(args.input, "r", encoding="utf-8")
		contents = infile.readlines()
		for sentences in alignments_final:
			for words in alignments_final[sentences]:
				val = alignments_final[sentences][words]
				if len(val) >= 2:
					lemma = return_field_conllu(find_str(sentences, contents), "form", words, "lemma").lower()
					if lemma != "_":
						if lemma in lemma_tags:
							_, pos = remove_ambiguity(lemma, lemma_tags)
							if _:
								val = pos[0]
							else:
								val = random.sample(pos, 1)[0]
						else:
							if words.lower() in words_and_pos:
								single_count, max_vals = remove_ambiguity(words.lower(), words_and_pos)
								
								# if more than one element in the returned list, select one at random
								if not single_count:
									val = random.sample(max_vals, 1)[0]
								else:
									val = max_vals[0]
				alignments_final[sentences][words] = val
		
		# refresh the POS dict
		words_and_pos = pos_encountered(alignments_final)
		print("Time for lemma/form based filling (part 1): " + str(datetime.now() - time_start))
	
	# PROBLEM 2
	
	# fill in the position with an older possible value from the pos-dict
	if not args.lemma_based_decision:
		time_start = datetime.now()
		total = 0
		count = 0
		for sentences in alignments_final:
			for words in alignments_final[sentences]:
				val = alignments_final[sentences][words]
				if len(val) == 0:
					total += 1
					if words.lower() in words_and_pos:
						count += 1
						single_count, max_vals = remove_ambiguity(words.lower(), words_and_pos)
						
						# if more than one element in the returned list, select one at random
						if not single_count:
							val = random.sample(max_vals, 1)
						else:
							val = max_vals
					
					# if word not in POS dictionary, handle it later
					else:
						pass
					
					alignments_final[sentences][words] = val
		
		words_and_pos = pos_encountered(alignments_final)
		print("Time for POS_based filling of blank values (part 2): " + str(datetime.now() - time_start))
		if total != 0:
			print(str(round((total - count) * 100 / total, 4)) + " % of originally_empty_values (" + str(total - count) + " of " + str(total) + ") remain unfilled.")
	
	# generate a dict of lemmas, and fill in the values based on the encountered lemmas.
	# if a lemma is not present, it would be filled in later using POS_dict, updated after all the other values are filled in.
	# the above mentioned step happens while writing the output file
	else:
		time_start = datetime.now()
		lemma_tags = get_lemma_based_tags(alignments_final)
		infile = open(args.input, "r", encoding="utf-8")
		contents = infile.readlines()
		total = 0
		count = 0
		for sentences in alignments_final:
			for words in alignments_final[sentences]:
				val = alignments_final[sentences][words]
				if len(val) == 0:
					total += 1
					lemma = return_field_conllu(find_str(sentences, contents), "form", words, "lemma")
					
					if lemma in lemma_tags:
						single_count, max_vals = remove_ambiguity(lemma.lower(), lemma_tags)
						count += 1
						
						# if more than one element in the returned list, select one at random
						if not single_count:
							val = random.sample(max_vals, 1)
						else:
							val = max_vals
					
					# if word not in lemma dictionary, handle it later with pos_dictionary
					else:
						pass
					alignments_final[sentences][words] = val
		
		# refresh the POS dict
		words_and_pos = pos_encountered(alignments_final)
		
		print("Time for Lemma_based filling of blank values (part 2): " + str(datetime.now() - time_start))
		if total != 0:
			print(str(round((total - count) * 100 / total, 4)) + " % of originally_empty_values (" + str(total - count) + " of " + str(total) + ") remain unfilled.")
	
	# In the end, for all remaining tokens, the rest of the tokens are given the POS_tag of "NOUN"
	# this will be handled while reading the outputs for all the non-empty values.
	
	# Having filled in the alignments entirely, we substitute the values token-by-token in the output file
	if args.output:
		print("Calculating Outputs now")
		time_start = datetime.now()
		outputs = write_output(alignments_final, words_and_pos)
		cat_val = ""
		if args.random_fill and args.lemma_based_decision:
			cat_val = "11"
		elif args.random_fill and not args.lemma_based_decision:
			cat_val = "10"
		elif not args.random_fill and args.lemma_based_decision:
			cat_val = "01"
		elif not args.random_fill and not args.lemma_based_decision:
			cat_val = "00"
		pickle.dump(outputs, open(folder + "/" + "output_pickle" + cat_val, "wb"))
		print("Outputs calculated in " + str(datetime.now() - time_start) + ", pickle stored in " + folder + "/" + "output_pickle" + cat_val + ".\nWriting outputs in file now.")
		ofile = ""
		if args.random_fill and args.lemma_based_decision:
			ofile = args.output + "11"
		elif args.random_fill and not args.lemma_based_decision:
			ofile = args.output + "10"
		elif not args.random_fill and args.lemma_based_decision:
			ofile = args.output + "01"
		elif not args.random_fill and not args.lemma_based_decision:
			ofile = args.output + "00"
		with open(ofile, "w", encoding="utf-8") as outfile:
			for i in outputs:
				outfile.write(i)
		print("Outputs written in " + ofile)
	
	print("\nFin")
