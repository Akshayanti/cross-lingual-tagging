#!/usr/bin/env bash

.PHONY: restoreData
.SILENT: restoreData

# pastes the data together, and then seperates into individual files, to lose empty lines.
clean_data: restoreData
	echo 'tel'
	paste tel/te.s tel/ta.s | grep -P '.\t.' > tel/tel-ta;
	paste tel/te.s tel/tur.s | grep -P '.\t.' > tel/tel-tur;
	paste tel/Run0/Setting2/te.s tel/Run0/Setting2/en.s | grep -P '.\t.' > tel/Run0/Setting2/tel-en;
	cut -f1 tel/tel-tur > tel/tel-tur.tel
	cut -f2 tel/tel-tur > tel/tel-tur.tur
	cut -f1 tel/tel-ta > tel/tel-ta.tel
	cut -f2 tel/tel-ta > tel/tel-ta.ta
	cut -f1 tel/tel-en > tel/tel-en.tel
	cut -f2 tel/tel-en > tel/tel-en.en

# aligns data mgiza, removes intermediate files.
align_data: restoreData
	echo 'tel'
	mkcls -n10 -ptel/tel-ta.tel -Vtel/tel-ta.tel.classes
	mkcls -n10 -ptel/tel-ta.ta -Vtel/tel-ta.ta.classes
	plain2snt tel/tel-ta.tel tel/tel-ta.ta
	snt2cooc tel/tel-ta.cooc tel/tel-ta.tel.vcb tel/tel-ta.ta.vcb tel/tel-ta.tel_tel-ta.ta.snt
	mgiza tel/config_ta
	mkcls -n10 -ptel/tel-tur.tel -Vtel/tel-tur.tel.classes
	mkcls -n10 -ptel/tel-tur.tur -Vtel/tel-tur.tur.classes
	plain2snt tel/tel-tur.tel tel/tel-tur.tur
	snt2cooc tel/tel-tur.cooc tel/tel-tur.tel.vcb tel/tel-tur.tur.vcb tel/tel-tur.tel_tel-tur.tur.snt
	mgiza tel/config_tur
	cat tel/ta*part* >> tel/ta_final
	cat tel/tur*part* >> tel/tur_final
	mkcls -n10 -ptel/tel-en.tel -Vtel/tel-en.tel.classes
	mkcls -n10 -ptel/tel-en.en -V tel/tel-en.en.classes
	plain2snt tel/tel-en.tel tel/tel-en.en
	snt2cooc tel/tel-en.cooc tel/tel-en.tel.vcb tel/tel-en.en.vcn tel/tel-en.tel_tel-en.en.snt
	mgiza tel/config_en
	rm */*part*
	rm */*.gizacfg
	rm */*classes*
	rm */*snt
	rm */*vcb
	rm */*cooc

UDpipe: restoreData
	echo 'tel'
	udpipe --tokenize --tokenizer=presegmented --tag $(HOME)/udpipe-ud*/telugu-*.udpipe < tel/te.s > tel/tel.conllu
	udpipe --tokenize --tokenizer=presegmented $(HOME)/udpipe-ud*/telugu-*.udpipe < tel/te.s > tel/tel_out.conllu
	udpipe --tokenize --tag --parse --tokenizer=presegmented $(HOME)/udpipe-ud*/tamil-*.udpipe < tel/ta.s > tel/ta.conllu
	udpipe --tokenize --tag --parse --tokenizer=presegmented $(HOME)/udpipe-ud*/turkish-*.udpipe < tel/tur.s > tel/tur.conllu
	udpipe --tokenize --tokenizer=presegmented --tag --parse $(HOME)/udpipe-ud*/telugu-*.udpipe < tel/test.txt > tel/tel_test.conllu
	udpipe --tokenize --tag --parse --tokenizer=presegmented $(HOME)/udpipe-ud*/english-ud*.udpipe < tel/en.s > tel/en.conllu

pickle: restoreData
	python3 align.py -i tel/tel.conllu -a tel/tur_final tel/ta_final -c tel/tur.conllu tel/ta.conllu --pickle

tag: restoreData
	echo 'tel'
	python3 align.py -i tel/tel.conllu -l tel/lang_scores -a tel/tur_final tel/ta_final -c tel/tur.conllu tel/ta.conllu --already_pickled sentence_pickle word_pickle -o tel/tel_out.conllu --random_fill
	python3 align.py -i tel/tel.conllu -l tel/lang_scores -a tel/tur_final tel/ta_final -c tel/tur.conllu tel/ta.conllu --already_pickled sentence_pickle word_pickle -o tel/tel_out.conllu --lemma_based_decision --random_fill
	python3 align.py -i tel/tel.conllu -l tel/lang_scores -a tel/tur_final tel/ta_final -c tel/tur.conllu tel/ta.conllu --already_pickled sentence_pickle word_pickle -o tel/tel_out.conllu --lemma_based_decision
	python3 align.py -i tel/tel.conllu -l tel/lang_scores -a tel/tur_final tel/ta_final -c tel/tur.conllu tel/ta.conllu --already_pickled sentence_pickle word_pickle -o tel/tel_out.conllu

train_models: restoreData
	udpipe --train tel/model00 --tokenizer=none --parser=none tel/tel_out.conllu00
	udpipe --train tel/model01 --tokenizer=none --parser=none tel/tel_out.conllu01
	udpipe --train tel/model10 --tokenizer=none --parser=none tel/tel_out.conllu10
	udpipe --train tel/model11 --tokenizer=none --parser=none tel_out.conllu11
	
train_accuracy: restoreData
	python3 training_accuracy.py --true tel/tel.conllu --generated tel/tel_out.conllu00 
	python3 training_accuracy.py --true tel/tel.conllu --generated tel/tel_out.conllu01 
	python3 training_accuracy.py --true tel/tel.conllu --generated tel/tel_out.conllu10 
	python3 training_accuracy.py --true tel/tel.conllu --generated tel/tel_out.conllu11
	
test_accuracy: restoreData
	udpipe --accuracy --tag tel/model00 tel/tel_test.conllu
	udpipe --accuracy --tag tel/model01 tel/tel_test.conllu
	udpipe --accuracy --tag tel/model10 tel/tel_test.conllu
	udpipe --accuracy --tag tel/model11 tel/tel_test.conllu

restoreData:
	if [ ! -d tel ]; then \
		cat data/data_source.part.* > data/data_source; \
		cd data; \
			tar -xf data_source; \
			mv tel ../; \
			rm -f data_source; \
		cd ..; \
	fi;