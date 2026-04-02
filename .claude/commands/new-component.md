Scaffold a new Pulumi ComponentResource in `infra/components/`.

Usage: `/new-component <ComponentName> [description]`

Steps:
1. Derive the filename: `infra/components/<component_name_snake>.py`
2. Use Context7 MCP to fetch current Pulumi Python ComponentResource docs:
   - Resolve: `mcp__claude_ai_Context7__resolve-library-id` with query `"pulumi python"`
   - Query: `mcp__claude_ai_Context7__query-docs` for `ComponentResource`
3. Generate the file with this structure:

```python
"""<ComponentName>: <description>"""
from __future__ import annotations
from typing import Optional
import pulumi
from pulumi import ComponentResource, Input, Output, ResourceOptions


class <ComponentName>Args:
    def __init__(
        self,
        # TODO: add typed args
    ) -> None:
        # assign args
        pass


class <ComponentName>(ComponentResource):
    # TODO: declare output type annotations

    def __init__(
        self,
        name: str,
        args: <ComponentName>Args,
        opts: Optional[ResourceOptions] = None,
    ) -> None:
        super().__init__("test:infra:<ComponentName>", name, None, opts)

        # TODO: create child resources with opts=ResourceOptions(parent=self)

        self.register_outputs({})
```

4. Add an export to `infra/components/__init__.py`.
5. Ask the user what cloud resources this component should manage before filling in the TODOs.
