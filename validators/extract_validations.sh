output_file=../data/validations.jsonl
touch $output_file

echo "-------------"
echo "Index file: $1"
echo "Output file: $output_file"

echo "extracting counts rules..."
./extract_counts.sh $1 > $output_file

echo "extracting contains rules..."
./extract_contains.sh $1 >> $output_file

echo "extracting contained_by rules..."
./extract_contained_by.sh $1 >> $output_file

echo "Done! saved at  $output_file"