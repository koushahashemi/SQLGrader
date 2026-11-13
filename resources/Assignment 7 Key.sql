-- 1. Display CompanyName and OrderDate by joining Customers and Orders
SELECT c.CompanyName, o.OrderDate
FROM Customers c
INNER JOIN Orders o ON c.CustomerID = o.CustomerID;


-- 2. Display CompanyName and Freight where Freight > 50
SELECT c.CompanyName, o.Freight
FROM Customers c
INNER JOIN Orders o ON c.CustomerID = o.CustomerID
WHERE o.Freight > 50;


-- 3. Display CompanyName and OrderDate using JOIN (no focus on alias requirement)
SELECT Customers.CompanyName, Orders.OrderDate
FROM Customers
INNER JOIN Orders ON Customers.CustomerID = Orders.CustomerID;


-- 4. Join multiple tables to display CompanyName, OrderDate, and ProductName
SELECT c.CompanyName, o.OrderDate, p.ProductName
FROM Customers c
INNER JOIN Orders o ON c.CustomerID = o.CustomerID
INNER JOIN [Order Details] od ON o.OrderID = od.OrderID
INNER JOIN Products p ON od.ProductID = p.ProductID;


-- 5. Display ProductName and Quantity ordered for each order
SELECT p.ProductName, od.Quantity
FROM [Order Details] od
INNER JOIN Products p ON od.ProductID = p.ProductID;


-- 6. Display ProductName and total inventory value (UnitPrice * UnitsInStock)
SELECT ProductName, UnitPrice * UnitsInStock AS InventoryValue
FROM Products;


-- 7. Total amount spent by each customer
SELECT c.CompanyName, SUM(od.UnitPrice * od.Quantity) AS TotalSpent
FROM Customers c
INNER JOIN Orders o ON c.CustomerID = o.CustomerID
INNER JOIN [Order Details] od ON o.OrderID = od.OrderID
GROUP BY c.CompanyName;


-- 8. Total quantity sold per product where total > 100 (uses HAVING)
SELECT p.ProductName, SUM(od.Quantity) AS TotalQuantity
FROM Products p
INNER JOIN [Order Details] od ON p.ProductID = od.ProductID
GROUP BY p.ProductName
HAVING SUM(od.Quantity) > 100;


-- 9. Orders after January 1, 1997
SELECT c.CompanyName, o.OrderDate
FROM Customers c
INNER JOIN Orders o ON c.CustomerID = o.CustomerID
WHERE o.OrderDate > '1997-01-01';


-- 10. Top 10 products with highest revenue
SELECT TOP 10 p.ProductName, SUM(od.UnitPrice * od.Quantity) AS Revenue
FROM Products p
INNER JOIN [Order Details] od ON p.ProductID = od.ProductID
GROUP BY p.ProductName
ORDER BY Revenue DESC;