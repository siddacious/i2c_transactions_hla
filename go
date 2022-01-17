#!/usr/bin/env bash
echo $1 was passed
fswatch -0 $1 | while read -d "" event ; do
	python $1
done
