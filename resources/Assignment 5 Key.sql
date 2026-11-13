-- 1. Total number of orders
SELECT COUNT(*) AS TotalOrders
FROM Orders;

-- 2. Average unit price of products
SELECT AVG(UnitPrice) AS AvgPrice
FROM Products;

-- 3. Minimum and maximum product prices
SELECT MIN(UnitPrice) AS MinPrice,
       MAX(UnitPrice) AS MaxPrice
FROM Products;

-- 4. Total quantity ordered
SELECT SUM(Quantity) AS TotalQuantity
FROM [Order Details];

-- 5. Total sales amount (UnitPrice * Quantity)
SELECT SUM(UnitPrice * Quantity) AS TotalSales
FROM [Order Details];

-- 6. Total sales per product
SELECT ProductID,
       SUM(UnitPrice * Quantity) AS TotalSales
FROM [Order Details]
GROUP BY ProductID;

-- 7. Number of orders per customer
SELECT CustomerID,
       COUNT(*) AS OrderCount
FROM Orders
GROUP BY CustomerID;

-- 8. Customers with more than 5 orders
SELECT CustomerID,
       COUNT(*) AS OrderCount
FROM Orders
GROUP BY CustomerID
HAVING COUNT(*) > 5;

-- 9. Products with price above average (subquery)
SELECT ProductName, UnitPrice
FROM Products
WHERE UnitPrice > (
    SELECT AVG(UnitPrice)
    FROM Products
);

-- 10. Total inventory value per product
SELECT ProductName,
       UnitPrice * UnitsInStock AS TotalValue
FROM Products;