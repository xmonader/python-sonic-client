# python-sonic-client
Python client for [sonic](https://github.com/valeriansaliou/sonic) search backend.


## Examples

### Ingest 

```python
def test_ingest():
    with IngestClient("127.0.0.1", 1491, 'dmdm') as ingestcl:
        print(ingestcl.ping())
        print(ingestcl.protocol)
        print(ingestcl.bufsize)
        ingestcl.push("wiki", "articles", "article-1",
                      "for the love of god hell")
        ingestcl.push("wiki", "articles", "article-2",
                      "for the love of satan heaven")
        ingestcl.push("wiki", "articles", "article-3",
                      "for the love of lorde hello")
        ingestcl.push("wiki", "articles", "article-4",
                      "for the god of loaf helmet")
```


### Search

```python
def test_search():
    with SearchClient("127.0.0.1", 1491, 'dmdm') as querycl:
        print(querycl.ping())
        print(querycl.query("wiki", "articles", "for"))
        print(querycl.query("wiki", "articles", "love"))
        print(querycl.suggest("wiki", "articles", "hell"))

```


## Difference from asonic
asonic uses asyncio and this client doesn't. It grew out of needing to use sonic within gevent context  
