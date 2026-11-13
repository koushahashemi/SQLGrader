-- =====================================
-- 1. Return all products (no parameters)
-- =====================================
CREATE PROCEDURE GetAllProducts
AS
BEGIN
    SET NOCOUNT ON;

    SELECT ProductName, UnitPrice, UnitsInStock
    FROM Products;
END;
GO


-- =====================================
-- 2. Get orders for a given customer
-- =====================================
CREATE PROCEDURE GetOrdersByCustomer
    @CustomerID NVARCHAR(5)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT OrderID, OrderDate, Freight
    FROM Orders
    WHERE CustomerID = @CustomerID;
END;
GO


-- =====================================
-- 3. Get products by category
-- =====================================
CREATE PROCEDURE GetProductsByCategory
    @CategoryID INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT ProductName, UnitPrice
    FROM Products
    WHERE CategoryID = @CategoryID;
END;
GO


-- =====================================
-- 4. Update product price
-- =====================================
CREATE PROCEDURE UpdateProductPrice
    @ProductID INT,
    @NewPrice MONEY
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE Products
    SET UnitPrice = @NewPrice
    WHERE ProductID = @ProductID;
END;
GO



-- =====================================
-- 5. Insert a new product and add it to OrderID 11012
-- =====================================
CREATE PROCEDURE AddProductAndSell
    @ProductName NVARCHAR(40),
    @SupplierID INT,
    @CategoryID INT,
    @UnitPrice MONEY,
    @UnitsInStock SMALLINT,
    @Quantity SMALLINT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ProductID INT;

    -- Insert new product
    INSERT INTO Products (ProductName, SupplierID, CategoryID, UnitPrice, UnitsInStock)
    VALUES (@ProductName, @SupplierID, @CategoryID, @UnitPrice, @UnitsInStock);

    -- Get the new ProductID
    SET @ProductID = SCOPE_IDENTITY();

    -- Insert into Order Details for OrderID 11012
    INSERT INTO [Order Details] (OrderID, ProductID, UnitPrice, Quantity)
    VALUES (11012, @ProductID, @UnitPrice, @Quantity);

    -- Show the inserted record
    SELECT *
    FROM [Order Details]
    WHERE OrderID = 11012 AND ProductID = @ProductID;
END;
GO