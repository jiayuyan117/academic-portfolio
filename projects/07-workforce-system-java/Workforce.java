import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * In-memory workforce index used to demonstrate data-structure invariants.
 * A department tree and employee BST share immutable employee records.
 */
public final class Workforce {
    public record Employee(int id, String name, int department, long salaryCents) {
        public Employee {
            if (id <= 0 || name == null || name.isBlank() || salaryCents < 0) {
                throw new IllegalArgumentException("Invalid employee");
            }
        }
    }

    private static final class Department {
        final int id;
        final List<Department> children = new ArrayList<>();
        final List<Integer> employees = new ArrayList<>();
        Department(int id) { this.id = id; }
    }

    private static final class Node {
        Employee employee;
        Node left;
        Node right;
        Node(Employee employee) { this.employee = employee; }
    }

    private final Map<Integer, Department> departments = new HashMap<>();
    private Node root;

    public Workforce() {
        departments.put(0, new Department(0));
    }

    private Department department(int id) {
        Department result = departments.get(id);
        if (result == null) throw new IllegalArgumentException("Unknown department");
        return result;
    }

    public void addDepartment(int id, int parent) {
        if (id <= 0 || departments.containsKey(id)) {
            throw new IllegalArgumentException("Duplicate or invalid department ID");
        }
        Department parentNode = department(parent);
        Department child = new Department(id);
        parentNode.children.add(child);
        departments.put(id, child);
    }

    public Employee find(int id) {
        Node node = root;
        while (node != null) {
            if (id == node.employee.id()) return node.employee;
            node = id < node.employee.id() ? node.left : node.right;
        }
        return null;
    }

    public void add(Employee employee) {
        Department target = department(employee.department());
        if (find(employee.id()) != null) throw new IllegalArgumentException("Duplicate employee ID");
        root = insert(root, employee);
        target.employees.add(employee.id());
    }

    private Node insert(Node node, Employee employee) {
        if (node == null) return new Node(employee);
        if (employee.id() < node.employee.id()) node.left = insert(node.left, employee);
        else node.right = insert(node.right, employee);
        return node;
    }

    public void transfer(int id, int destination) {
        Department target = department(destination);
        Employee employee = find(id);
        if (employee == null) throw new IllegalArgumentException("Unknown employee");
        if (employee.department() == destination) return;
        Department old = department(employee.department());
        Node node = root;
        while (node.employee.id() != id) {
            node = id < node.employee.id() ? node.left : node.right;
        }
        old.employees.remove(Integer.valueOf(id));
        target.employees.add(id);
        node.employee = new Employee(id, employee.name(), destination, employee.salaryCents());
    }

    public void remove(int id) {
        Employee employee = find(id);
        if (employee == null) throw new IllegalArgumentException("Unknown employee");
        root = delete(root, id);
        department(employee.department()).employees.remove(Integer.valueOf(id));
    }

    private Node delete(Node node, int id) {
        if (id < node.employee.id()) node.left = delete(node.left, id);
        else if (id > node.employee.id()) node.right = delete(node.right, id);
        else {
            if (node.left == null) return node.right;
            if (node.right == null) return node.left;
            Node successor = node.right;
            while (successor.left != null) successor = successor.left;
            node.employee = successor.employee;
            node.right = delete(node.right, successor.employee.id());
        }
        return node;
    }

    public List<Employee> sortedEmployees() {
        List<Employee> result = new ArrayList<>();
        traverse(root, result);
        return List.copyOf(result);
    }

    private void traverse(Node node, List<Employee> result) {
        if (node == null) return;
        traverse(node.left, result);
        result.add(node.employee);
        traverse(node.right, result);
    }

    public int count(int departmentId) {
        return count(department(departmentId));
    }

    private int count(Department node) {
        return node.employees.size() + node.children.stream().mapToInt(this::count).sum();
    }

    public List<Employee> salaryRange(long minimum, long maximum) {
        if (minimum < 0 || maximum < minimum) throw new IllegalArgumentException("Invalid range");
        return sortedEmployees().stream()
                .filter(e -> e.salaryCents() >= minimum && e.salaryCents() <= maximum)
                .toList();
    }

    public void verify() {
        Map<Integer, Integer> memberships = new HashMap<>();
        for (Department department : departments.values()) {
            for (int id : department.employees) {
                Employee employee = find(id);
                if (employee == null || employee.department() != department.id) {
                    throw new IllegalStateException("Organization/BST mismatch");
                }
                memberships.merge(id, 1, Integer::sum);
            }
        }
        List<Employee> all = sortedEmployees();
        int previous = 0;
        for (Employee employee : all) {
            if (employee.id() <= previous || memberships.getOrDefault(employee.id(), 0) != 1) {
                throw new IllegalStateException("Duplicate, missing or unordered employee");
            }
            previous = employee.id();
        }
        if (count(0) != all.size()) throw new IllegalStateException("Count mismatch");
    }

    public static void main(String[] args) {
        Workforce app = new Workforce();
        app.addDepartment(10, 0);
        app.addDepartment(20, 0);
        app.add(new Employee(100, "Demo Analyst", 10, 650000));
        app.transfer(100, 20);
        app.verify();
        System.out.println("Synthetic demo: " + app.sortedEmployees());
        System.out.println("Organization and employee index are consistent.");
    }
}
