import java.io.IOException;
import java.math.BigDecimal;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Small single-process catalog. Publish memory only after the snapshot commits. */
public final class Catalog implements AutoCloseable {
    public record Product(String sku, String name, long cents, int stock, long version) {
        public Product {
            if (sku == null || !sku.matches("[A-Z0-9-]{1,24}"))
                throw new IllegalArgumentException("SKU: 1-24 uppercase letters, digits or hyphens");
            if (name == null || name.isBlank() || name.length() > 100
                    || name.codePoints().anyMatch(Character::isISOControl))
                throw new IllegalArgumentException("Name: 1-100 characters, no control characters");
            if (cents < 0 || cents > 100_000_000 || stock < 0 || stock > 1_000_000 || version < 1)
                throw new IllegalArgumentException("Price, stock or version out of range");
        }
    }
    public static final class Conflict extends IllegalArgumentException {
        public Conflict() { super("Catalog changed. Reload before editing."); }
    }
    private final Path file;
    private final FileChannel lockChannel;
    private final FileLock lock;
    private SortedMap<String, Product> products = new TreeMap<>();
    // Global revision prevents stale forms from matching a deleted/recreated SKU.
    private long revision;

    public Catalog(Path file) throws IOException {
        this.file = file.toAbsolutePath();
        Files.createDirectories(this.file.getParent());
        lockChannel = FileChannel.open(Path.of(this.file + ".lock"),
                StandardOpenOption.CREATE, StandardOpenOption.WRITE);
        FileLock acquired;
        try {
            acquired = lockChannel.tryLock();
            if (acquired == null) throw new IOException("Catalog is already open");
        } catch (IOException | RuntimeException e) {
            lockChannel.close();
            throw e;
        }
        lock = acquired;
        try {
            if (Files.exists(this.file)) {
                List<String> lines = Files.readAllLines(this.file, StandardCharsets.UTF_8);
                String[] header = lines.get(0).split("\t");
                if (header.length != 2 || !header[0].equals("CATALOG-1")) throw new IOException("Invalid header");
                revision = Long.parseLong(header[1]);
                if (revision < 0) throw new IOException("Invalid revision");
                for (String line : lines.subList(1, lines.size())) {
                    String[] f = line.split("\t", -1);
                    if (f.length != 5) throw new IOException("Invalid row");
                    Product p = new Product(f[0], f[1], Long.parseLong(f[2]),
                            Integer.parseInt(f[3]), Long.parseLong(f[4]));
                    if (p.version() > revision || products.put(p.sku(), p) != null)
                        throw new IOException("Invalid or duplicate versioned row");
                }
            }
        } catch (IOException | RuntimeException e) {
            close();
            throw new IOException("Cannot load catalog; original file retained", e);
        }
    }

    public static long price(String input) {
        if (input == null || !input.matches("[0-9]{1,7}(\\.[0-9]{1,2})?"))
            throw new IllegalArgumentException("Price must be a nonnegative decimal with at most two places");
        long cents = new BigDecimal(input).movePointRight(2).longValueExact();
        if (cents > 100_000_000) throw new IllegalArgumentException("Price exceeds 1000000.00");
        return cents;
    }
    public synchronized List<Product> list(String query) {
        String q = query.toLowerCase(Locale.ROOT);
        return products.values().stream().filter(p -> p.sku().toLowerCase(Locale.ROOT).contains(q)
                || p.name().toLowerCase(Locale.ROOT).contains(q)).toList();
    }
    public synchronized void save(String sku, String name, String price, int stock, long expected)
            throws IOException {
        if (sku == null) throw new IllegalArgumentException("SKU required");
        Product old = products.get(sku);
        if ((old == null && expected != 0) || (old != null && expected != old.version()))
            throw new Conflict();
        if (old == null && products.size() >= 1000) throw new IllegalArgumentException("Limit: 1000 products");
        long next = Math.incrementExact(revision);
        Product p = new Product(sku, name, price(price), stock, next);
        SortedMap<String, Product> copy = new TreeMap<>(products);
        copy.put(sku, p);
        commit(copy, next);
    }
    public synchronized void delete(String sku, long expected) throws IOException {
        if (sku == null) throw new IllegalArgumentException("SKU required");
        Product old = products.get(sku);
        if (old == null || expected != old.version()) throw new Conflict();
        SortedMap<String, Product> copy = new TreeMap<>(products);
        copy.remove(sku);
        commit(copy, Math.incrementExact(revision));
    }
    private void commit(SortedMap<String, Product> next, long nextRevision) throws IOException {
        StringBuilder text = new StringBuilder("CATALOG-1\t" + nextRevision + "\n");
        for (Product p : next.values()) text.append(p.sku()).append('\t').append(p.name())
                .append('\t').append(p.cents()).append('\t').append(p.stock())
                .append('\t').append(p.version()).append('\n');
        Path temp = Files.createTempFile(file.getParent(), ".catalog-", ".tmp");
        try {
            Files.writeString(temp, text, StandardCharsets.UTF_8);
            try (FileChannel channel = FileChannel.open(temp, StandardOpenOption.WRITE)) { channel.force(true); }
            // No non-atomic fallback: unsupported filesystems fail without publishing new memory.
            Files.move(temp, file, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            products = next;
            revision = nextRevision;
        } finally { Files.deleteIfExists(temp); }
    }
    @Override public void close() throws IOException {
        try { lock.release(); } finally { lockChannel.close(); }
    }
}
