
package ie.tcd.cranfield;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;

import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.StringField;
import org.apache.lucene.document.TextField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.index.IndexWriterConfig.OpenMode;
import org.apache.lucene.queryparser.classic.MultiFieldQueryParser;
import org.apache.lucene.queryparser.classic.ParseException;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.search.similarities.BM25Similarity;
import org.apache.lucene.search.similarities.ClassicSimilarity;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;
import org.apache.lucene.analysis.en.EnglishAnalyzer;

public class CranfieldIR {

    private static final Path BASE = Paths.get(".").toAbsolutePath().normalize();
    private static final Path DATA = BASE.resolve("data");
    private static final Path INDEX = BASE.resolve("index");
    private static final Path RESULTS = BASE.resolve("results");

    private static final int TOP_K = 50;
    private static String selectedAnalyzer = "standard";

    static class Record {
        String id;
        String title = "";
        String text = "";

        Record(String id) {
            this.id = id;
        }
    }


    private static List<Record> readRecords(Path file) throws IOException {
        List<Record> records = new ArrayList<>();

        try (BufferedReader reader =
                 Files.newBufferedReader(file, StandardCharsets.UTF_8)) {

            Record current = null;
            String section = "";
            String line;

            while ((line = reader.readLine()) != null) {
                if (line.startsWith(".I")) {
                    if (current != null) {
                        records.add(current);
                    }

                    String id = String.valueOf(records.size()+1);  
                    current = new Record(id);
                    section = "";
                } else if (line.startsWith(".T")) {
                    section = "T";
                } else if (line.startsWith(".W")) {
                    section = "W";
                } else if (line.startsWith(".")) {
                    section = "";
                } else if (current != null) {
                    if (section.equals("T")) {
                        current.title += line + " ";
                    } else if (section.equals("W")) {
                        current.text += line + " ";
                    }
                }
            }

            if (current != null) {
                records.add(current);
            }
        }

        return records;
    }

    private static Analyzer createAnalyzer() {
        if(selectedAnalyzer.equals("standard")){
           return new StandardAnalyzer();
        } else {
           return new EnglishAnalyzer();
        }
    }

    private static void indexDocuments() throws IOException {
        Files.createDirectories(INDEX);

        List<Record> documents =
            readRecords(DATA.resolve("cran.all.1400"));

        try (Analyzer analyzer = createAnalyzer();
             Directory directory = FSDirectory.open(INDEX)) {

            IndexWriterConfig config = new IndexWriterConfig(analyzer);
            config.setOpenMode(OpenMode.CREATE);

            try (IndexWriter writer = new IndexWriter(directory, config)) {
                for (Record record : documents) {
                    Document document = new Document();

                    document.add(new StringField(
                        "id", record.id, Field.Store.YES));

                    document.add(new TextField(
                        "title", record.title, Field.Store.NO));

                    document.add(new TextField(
                        "text", record.text, Field.Store.NO));

                    writer.addDocument(document);
                }
            }
        }

        System.out.println("Documents read: " + documents.size());
        System.out.println("Index created at: " + INDEX);
    }

    private static void search(String method)
            throws IOException, ParseException {

        Files.createDirectories(RESULTS);

        List<Record> queries = readRecords(DATA.resolve("cran.qry"));

        Path output = RESULTS.resolve(method + "-" + selectedAnalyzer + ".run");
        String runName = "cranfield-" + method + "-" + selectedAnalyzer;

        try (Analyzer analyzer = createAnalyzer();
             Directory directory = FSDirectory.open(INDEX);
             DirectoryReader reader = DirectoryReader.open(directory);
             BufferedWriter writer = Files.newBufferedWriter(
                 output, StandardCharsets.UTF_8,
                 StandardOpenOption.CREATE,
                 StandardOpenOption.TRUNCATE_EXISTING,
                 StandardOpenOption.WRITE)) {

            IndexSearcher searcher = new IndexSearcher(reader);

            if (method.equals("vsm")) {
                searcher.setSimilarity(new ClassicSimilarity());
            } else if (method.equals("bm25")) {
                searcher.setSimilarity(new BM25Similarity());
            } else {
                throw new IllegalArgumentException(
                    "Method must be vsm or bm25");
            }

            MultiFieldQueryParser parser =
                new MultiFieldQueryParser(
                    new String[] {"title", "text"}, analyzer);

            int searched = 0;

            for (Record queryRecord : queries) {
                String queryText = queryRecord.text.trim();

                if (queryText.isEmpty()) {
                    System.err.println(
                        "Skipping empty query ID " + queryRecord.id);
                    continue;
                }

                Query query = parser.parse(
                    MultiFieldQueryParser.escape(queryText));

                TopDocs hits = searcher.search(query, TOP_K);

                int rank = 1;

                for (ScoreDoc hit : hits.scoreDocs) {
                    Document result = searcher.doc(hit.doc);
                    String documentId = result.get("id");

                    writer.write(
                        queryRecord.id + " Q0 " +
                        documentId + " " +
                        rank + " " +
                        hit.score + " " +
                        runName);

                    writer.newLine();
                    rank++;
                }

                searched++;
            }

            System.out.println("Queries searched: " + searched);
            System.out.println("Method: " + method);
            System.out.println("Results written to: " + output);
        }
    }

   public static void main(String[] args) throws Exception {
    try (Scanner scanner = new Scanner(System.in)) {
        while (true) {
            System.out.println("\nSelected analyzer: " + selectedAnalyzer);
            System.out.println("1. Select StandardAnalyzer");
            System.out.println("2. Select EnglishAnalyzer");
            System.out.println("3. Build/rebuild index");
            System.out.println("4. Run VSM");
            System.out.println("5. Run BM25");
            System.out.println("0. Exit");
            System.out.print("Choose an option: ");

            String choice = scanner.nextLine().trim();

            switch (choice) {
                case "1":
                    selectedAnalyzer = "standard";
                    System.out.println("StandardAnalyzer selected.");
                    break;
                case "2":
                    selectedAnalyzer = "english";
                    System.out.println("EnglishAnalyzer selected.");
                    break;
                case "3":
                    indexDocuments();
                    break;
                case "4":
                    search("vsm");
                    break;
                case "5":
                    search("bm25");
                    break;
                case "0":
                    System.out.println("Exiting.");
                    return;
                default:
                    System.out.println("Invalid choice. Choose 0, 1, 2, 3, 4, or 5.");
            }
        }
    }
}

 }       
