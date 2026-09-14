// This tool connects to the Mintlify MCP Server, which accesses and searches the Xano Documentation based on a search query.
tool search_xano_docs {
  instructions = "This allows you to search the Xano Documentation and input a search query. It will return a pages of the Xano Documentation based on the search query. This can be used to answer and analyze questions around Xano and how to use it."

  input {
    text search? filters=trim
  }

  stack {
    ai.external.mcp.tool.run {
      url = "https://docs.xano.com/mcp"
      bearer_token = ""
      connection_type = "stream"
      tool = "SearchXanoDocumentation"
      args = {}|set:"query":$input.search
    } as $search_xano_docs
  }

  response = $search_xano_docs
  tags = ["xano:quick-start"]
  guid = "ymRT49Md60QidiUPKkfZRBypBw8"
}