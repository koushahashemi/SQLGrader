-- ============================================
-- Northwind SQL Queries (SQL Server)
-- ============================================

-- 1. Display CompanyName, uppercase version, and number of characters
SELECT 
    CompanyName,
    UPPER(CompanyName) AS CompanyName_Upper,
    LEN(CompanyName) AS NameLength
FROM Customers;


-- 2. Display OrderID, OrderDate, and Order Year for orders in 1997
SELECT 
    OrderID,
    OrderDate,
    YEAR(OrderDate) AS OrderYear
FROM Orders
WHERE YEAR(OrderDate) = 1997;


-- 3. Display ProductName, UnitPrice, and rounded price (no decimals)
-- Only include products with UnitPrice > 20
SELECT 
    ProductName,
    UnitPrice,
    ROUND(UnitPrice, 0) AS RoundedPrice
FROM Products
WHERE UnitPrice > 20;


-- 4. Display CustomerID, CompanyName, and Region
-- Replace NULL Region values with 'Unknown'
-- Only include customers from USA
SELECT 
    CustomerID,
    CompanyName,
    ISNULL(Region, 'Unknown') AS Region
FROM Customers
WHERE Country = 'USA';


-- 5. Display ProductName, UnitPrice, and price after a 10% increase
-- Sort by increased price from highest to lowest
SELECT 
    ProductName,
    UnitPrice,
    UnitPrice * 1.10 AS IncreasedPrice
FROM Products
ORDER BY IncreasedPrice DESC;