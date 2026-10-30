# Cranfield IR Demo

## Connect to the VM

1. Open PuTTY.exe
2. In session, write the public IP address and port 22.
3. Go to connections -> ssh -> auth -> credentials.
4. Add the .ppk file.
5. Click on **Open**.
6. Enter the username: `azureuser`.

## Connect for streamlit session

1. Open PuTTY.exe
2. In session, write the public IP address and port 22.
3. Go to connections -> ssh -> tunnels.

- **Source port:** `8501`
- **Destination:** `127.0.0.1:8501`

4. Click on **Add**.
5. Go to connections -> ssh -> auth -> credentials.
6. Add the .ppk file.
7. Click on **Open**.
8. Enter the username: `azureuser`

## View the project files

In a PuTTY terminal:

```bash
cd ~/cranfield-ir
find . -maxdepth 4 -type f
```

## Build and run Java

```bash
cd ~/cranfield-ir
mvn clean package
java -jar target/cranfield-ir-1.0.jar
```

Use the menu to create the four search runs:

1. Enter `1` for StandardAnalyzer.
2. Enter `3` to build the index, `4` to run VSM, and `5` to run BM25.
3. Enter `2` for EnglishAnalyzer.
4. Enter `3` to rebuild the index, `4` to run VSM, and `5` to run BM25.
5. Enter `0` to exit the menu.

## View run files

```bash
ls results/*-standard.run results/*-english.run
less results/bm25-english.run
```

Press `q` to exit `less`. Replace the filename to view another run.

## Regenerate evaluation scores

```bash
mkdir -p results/evaluation

~/trec_eval-9.0.7/trec_eval -c -l 1 -m map -m recall.50 results/qrels.trec results/vsm-standard.run > results/evaluation/vsm-standard.txt
~/trec_eval-9.0.7/trec_eval -c -l 1 -m map -m recall.50 results/qrels.trec results/bm25-standard.run > results/evaluation/bm25-standard.txt
~/trec_eval-9.0.7/trec_eval -c -l 1 -m map -m recall.50 results/qrels.trec results/vsm-english.run > results/evaluation/vsm-english.txt
~/trec_eval-9.0.7/trec_eval -c -l 1 -m map -m recall.50 results/qrels.trec results/bm25-english.run > results/evaluation/bm25-english.txt
```

Display the scores with their method and analyzer labels:

```bash
for f in results/evaluation/*.txt; do
  case "$f" in
    *bm25-english*) label="BM25 - EnglishAnalyzer" ;;
    *bm25-standard*) label="BM25 - StandardAnalyzer" ;;
    *vsm-english*) label="VSM - EnglishAnalyzer" ;;
    *vsm-standard*) label="VSM - StandardAnalyzer" ;;
  esac
  echo "=== $label ==="
  cat "$f"
done
```

## Open the Streamlit UI

In a second PuTTY session, configure the local tunnel described above, then run:

```bash
cd ~/cranfield-ir
source .venv/bin/activate
streamlit run ui/app.py --server.address 127.0.0.1 --server.port 8501
```

Open **http://localhost:8501** in your computer’s browser. Keep the PuTTY connection and Streamlit terminal open while using the UI. Press **Ctrl+C** in the Streamlit terminal to stop it.

## Edit the Streamlit file

```bash
cd ~/cranfield-ir
nano ui/app.py
```
Save changes in Nano with **Ctrl+O**, press **Enter**, then exit with **Ctrl+X**.
