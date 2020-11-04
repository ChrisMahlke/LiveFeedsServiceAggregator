### ServiceValidator
#### Validate item
- Requirements for check
Accessible and valid item ID
- Results
Success -   Item is accessible in ArcGIS Online
            Obtain meta-data (Title, Snippet)
            Validate service
            Validate layers
            Obtain usage statistics
            Obtain feature counts
Error   -   Item is either Private or Invalid
            Does not exist
            Validate service
            Validate layers
            Use meta-data from previous run (do not over-write data model)
            Use usage statistics from previous run (do not over-write data model)

------------

#### Validate service
- Requirements for check
If the item it not accessible, the service url on file (config file) can be used
- Results
Success -   Record response
            Run checks against alfp results
            Validate layers
Error   -   Use feature counts from previous run (do not over-write data model)

------------

#### Validate service layers
- Requirements for check
Service url on the item or on file must be accessible
- Results
Success -   Obtain feature counts
Error   -   Use feature counts from previous run (do not over-write data model)
---------------------------
#### Validate usage statistics
- Requirements for check
Item must be accessible
- Results
Success -   Obtain usage statistics
Error   -   Use usage statistics from previous run (do not over-write data model)
---------------------------
#### Obtain feature counts
- Requirements for check
Service and Layers must be accessible
- Results
Success -   Obtain feature counts
Error   -   Use feature counts from previous run (do not over-write data model)