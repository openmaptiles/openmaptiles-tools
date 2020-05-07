.PHONY: README.md
README.md:
	sed -n -i'' -e '1,/<!-- DO NOT EDIT BELOW/p' $@
	cat $$(ls -1 *.sql | sort) | grep -Pzo '(?s)\/[*]+.*?[*]+\/' | sed 's/^[\/\*]\+.*/\n/' >> $@
