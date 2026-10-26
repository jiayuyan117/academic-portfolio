import java.util.List;

/**
 * Runnable evidence manifest for the portfolio reconstruction.
 *
 * This is intentionally not presented as the missing Java Web server.
 */
public final class PortfolioFacts {
    private PortfolioFacts() {}

    public static void main(String[] args) {
        List<String> facts = List.of(
                "Project 07: Personal Learning Knowledge Base",
                "Confirmed stack: Java 21, embedded Tomcat 9.0.111, Servlet 4.0, JSP/EL/JSTL, JDBC, H2 2.3.232",
                "Confirmed scope: users, materials, attachments, keyword search, ownership checks",
                "Confirmed security topics: password hashing, remember-me tokens, CSRF, multipart limits",
                "Reported verification: 66 integration checks and a 390px mobile check",
                "Checkout limitation: original Java Web source and runtime dependencies are absent",
                "Pending: tags, status workflow, content sniffing, backup, deployment, atomic file/DB transactions"
        );
        facts.forEach(System.out::println);
    }
}
