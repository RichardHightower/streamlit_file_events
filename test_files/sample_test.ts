
// Sample TypeScript File
console.log("Welcome to TypeScript!");

// Simple type annotation
function add(a: number, b: number): number {
    return a + b;
}

console.log(`Sum: ${add(3, 5)}`);

// Simple interface
interface Person {
    name: string;
    age: number;
}

const person: Person = {
    name: "Bob",
    age: 30
};

console.log(`Name: ${person.name}, Age: ${person.age}`);

// Simple tuple example
const tuple: [string, number] = ["John", 40];
console.log(`Tuple: ${tuple[0]}, ${tuple[1]}`);
