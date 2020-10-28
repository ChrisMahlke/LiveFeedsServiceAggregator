## Live Feeds Status and Health check

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

### Background

This Python script checks the status and health of the Living Atlas live feeds services.  It returns a `Response` object that can be used to dissect and inspect the results of the request.

## Contributing

In general, we follow the "fork-and-pull" Git workflow.

1. Fork the repo on GitHub
2. Clone the project to your own machine
3. Work on your fork
    1. Make your changes and additions
    2. Change or add tests if needed
    3. Run tests and make sure they pass
    4. Add changes to README.md if needed
4. Commit changes to your own branch
5. **Make sure** you merge the latest from "upstream" and resolve conflicts if there is any
6. Repeat step 3(3) above
7. Push your work back up to your fork
8. Submit a Pull request so that we can review your changes


### Status checks

- Is ArcGIS Online (or the Portal) responding to requests, or is ArcGIS currently down

- Are the Live Feeds (ArcGIS Online item IDs) valid and returning an ArcGIS Online Item
  (Note: It is possible and item could have been unshared with the public, rendering the item not accessible)

- Is the service (item URL) within the Live Feed valid and returning a response

  - Was there a timeout when attempting to get a response from the service
  - How many (if any) retires did it take to receive a response
  - Was the maximum number of retries exceeded

- Check if the service's usage statistics can be retrieved

- Check if the layers within the service are responding

  - The service can be accessible, but the layers may not be accessible


Notes:

When using `requests`, especially in a production application environment, it’s important to consider performance implications. Features like *timeout control*, *sessions*, and *retry* limits can help you keep your application running smoothly.



### Response

- `statusPreparedOn` The date the status of the item was generated

	- `items` An array of *n* items
	
		- `id` The unique ID for this item
		
		- `title` The title of the item. This is the name that is displayed to users and by which they refer to the item. Every item must have a title.
		
		- `snippet` A short summary description of the item.
		
		- `lastUpdateTime` The last update time of the feed
		
		- `updateRate` The update rate of the item
		
		- `featureCount` The total number of features in the servvice (after any layers have been excluded from validation)
		
		- `usage` Usage details related to the service (i.e. how many requests over a specified period of time have been made to the service)
		
			- `trendingCode`  A numeric value indicating if the usage is not increasing or decreasing (**0**), increasing (**1**), or decreasing (**-1**)
			
			- `percentChange` The trending percent change (this valud can be negative if the trending is down)
			
			- `usageCounts` An array indicating the exact number of request.  The first index is the past hour, and the second index represents that last 6 hour average.
			
		- `status` A dictionary containing the code that reflects the status of the item
		
			- `code` A code that can be mapped to indicated the status of the item.  For example, 000 is a status that indicates everything is operating normally for this specific service.
			

```json
{
	"statusPreparedOn": 1603765716,
	"items": [{
		"id": "a6134ae01aad44c499d12feec782b386",
		"title": "USA Weather Watches and Warnings",
		"snippet": "A live data feed from the National Weather Service containing official weather warnings, watches, and advisory statements for the United States.",
		"lastUpdateTime": 1603765260,
		"updateRate": 10,
		"featureCount": 7560,
		"usage": {
			"trendingCode": 2,
			"percentChange": -100,
			"usageCounts": [0,100]
      	},
      	"status": {
	  		"code": "000"
		}
	}]
}
```

### Maintainers

[pauldodd]() - **Paul Dodd** (author)

[chrismahlke](https://github.com/ChrisMahlke) - **Chris Mahlke** (author)


### License

```
Copyright (c) 2020 Esri

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```````
