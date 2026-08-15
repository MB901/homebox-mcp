"""MCP Tools for Homebox inventory management."""

import base64
import binascii
from typing import Any

from fastmcp import FastMCP

from homebox_client import HomeboxClient


def register_tools(mcp: FastMCP, client: HomeboxClient) -> None:
    """Register all Homebox tools with the MCP server.

    Args:
        mcp: The FastMCP server instance.
        client: The Homebox API client.
    """

    # =========================================================================
    # Location Tools
    # =========================================================================

    @mcp.tool()
    async def homebox_list_locations() -> list[dict[str, Any]]:
        """List all locations in the inventory as a flat list.

        Returns the complete list of locations registered in Homebox, without
        parent/children relationships (kept intentionally simple). Use
        homebox_get_location_tree() for full hierarchy or homebox_get_location()
        for a single location's parent/children details.

        Returns:
            List of locations with id, name, description, and item_count.
        """
        locations = await client.get_locations()
        return [
            {
                "id": loc.get("id"),
                "name": loc.get("name"),
                "description": loc.get("description", ""),
                "item_count": loc.get("itemCount", 0),
            }
            for loc in locations
        ]

    @mcp.tool()
    async def homebox_get_location_tree() -> list[dict[str, Any]]:
        """Get the complete location hierarchy tree.

        Fetches all locations and assembles them into a hierarchy based on
        their parent relationships. Use this when you need to understand the
        full location hierarchy (e.g. to find where to nest a new location).

        Returns:
            List of root locations (no parent), each with nested children array.
            Each location contains: id, name, description, item_count, children[].
        """
        return await client.get_location_tree()

    @mcp.tool()
    async def homebox_get_location(location_id: str) -> dict[str, Any]:
        """Get details of a specific location including hierarchy info.

        This endpoint returns full location details INCLUDING parent and
        children relationships, unlike list_locations which doesn't include
        hierarchy information.

        Args:
            location_id: Location ID (UUID).

        Returns:
            Complete location details including:
            - id, name, description
            - parent: {id, name} if this location has a parent
            - children: entities (sub-locations and/or items) directly
              inside this location
            - itemCount: number of items stored in this location
        """
        return await client.get_location(location_id)

    @mcp.tool()
    async def homebox_create_location(
        name: str,
        description: str | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new location in the inventory.

        Use this tool to create new places where items can be stored,
        such as rooms, cabinets, drawers, etc.

        Args:
            name: Location name (required).
            description: Optional location description.
            parent_id: Parent location ID to create hierarchy.
                       For example, "Drawer 1" can be a child of "Desk".

        Returns:
            Created location with all fields.
        """
        return await client.create_location(name, description, parent_id)

    @mcp.tool()
    async def homebox_update_location(
        location_id: str,
        name: str | None = None,
        description: str | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing location.

        Args:
            location_id: Location ID (UUID) to update.
            name: New name (optional).
            description: New description (optional).
            parent_id: New parent location ID (optional).

        Returns:
            Updated location.
        """
        return await client.update_location(location_id, name, description, parent_id)

    @mcp.tool()
    async def homebox_delete_location(location_id: str) -> str:
        """Remove a location from the inventory.

        WARNING: The location must not have items or sub-locations.

        Args:
            location_id: Location ID (UUID) to remove.

        Returns:
            Confirmation message.
        """
        await client.delete_location(location_id)
        return f"Location {location_id} successfully removed."

    # =========================================================================
    # Item Tools
    # =========================================================================

    @mcp.tool()
    async def homebox_list_items(
        location_id: str | None = None,
        label_id: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """List inventory items with optional filters.

        Use this tool to get a list of items. You can filter by location,
        label, or perform a text search.

        Args:
            location_id: Filter by specific location (UUID).
            label_id: Filter by specific label (UUID).
            search: Search term for item name/description.

        Returns:
            List of items with id, name, location, quantity, etc.
        """
        items = await client.get_items(location_id, label_id, search)
        return [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "description": item.get("description", ""),
                "quantity": item.get("quantity", 1),
                "location": {
                    "id": item.get("location", {}).get("id"),
                    "name": item.get("location", {}).get("name"),
                },
                "labels": [
                    {"id": label.get("id"), "name": label.get("name")}
                    for label in item.get("labels", [])
                ],
                "insured": item.get("insured", False),
                "archived": item.get("archived", False),
            }
            for item in items
        ]

    @mcp.tool()
    async def homebox_get_item(item_id: str) -> dict[str, Any]:
        """Get complete details of a specific item.

        Use this tool when you need all information about an item,
        including fields like serial number, manufacturer, price, etc.

        Args:
            item_id: Item ID (UUID).

        Returns:
            Complete item details including all fields.
        """
        return await client.get_item(item_id)

    @mcp.tool()
    async def homebox_search(query: str) -> list[dict[str, Any]]:
        """Flexible search for items in the inventory.

        Performs a text search on item names and descriptions.

        Args:
            query: Search term (name, description, etc).

        Returns:
            List of items matching the search.
        """
        items = await client.get_items(search=query)
        return [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "description": item.get("description", ""),
                "quantity": item.get("quantity", 1),
                "location": {
                    "id": item.get("location", {}).get("id"),
                    "name": item.get("location", {}).get("name"),
                },
            }
            for item in items
        ]

    @mcp.tool()
    async def homebox_create_item(
        name: str,
        location_id: str,
        description: str | None = None,
        quantity: int = 1,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new item in the inventory.

        Use this tool to add new items to the inventory.

        Args:
            name: Item name (required).
            location_id: Location ID (UUID) where the item will be stored.
            description: Item description (optional).
            quantity: Item quantity (default: 1).
            labels: List of label IDs (UUIDs) to associate with the item.

        Returns:
            Created item with all fields.
        """
        return await client.create_item(name, location_id, description, quantity, labels)

    @mcp.tool()
    async def homebox_update_item(
        item_id: str,
        name: str | None = None,
        description: str | None = None,
        quantity: int | None = None,
        location_id: str | None = None,
        labels: list[str] | None = None,
        insured: bool | None = None,
        archived: bool | None = None,
        asset_id: str | None = None,
        serial_number: str | None = None,
        model_number: str | None = None,
        manufacturer: str | None = None,
        lifetime_warranty: bool | None = None,
        warranty_expires: str | None = None,
        warranty_details: str | None = None,
        purchase_price: float | None = None,
        purchase_date: str | None = None,
        purchase_from: str | None = None,
        sold_date: str | None = None,
        sold_to: str | None = None,
        sold_price: float | None = None,
        sold_notes: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Update fields of an existing item.

        Use this tool to modify any field of an item.
        Only the provided fields will be updated.

        Args:
            item_id: Item ID (UUID) to update (required).
            name: New item name.
            description: New description.
            quantity: New quantity.
            location_id: New location ID (moves the item).
            labels: New list of label IDs.
            insured: Insurance status (true/false).
            archived: Archived status (true/false).
            asset_id: Asset/property ID.
            serial_number: Serial number.
            model_number: Model number.
            manufacturer: Manufacturer.
            lifetime_warranty: Lifetime warranty flag (true/false). Requires
                Homebox v0.26.0+; ignored on older Homebox versions.
            warranty_expires: Warranty expiration date, as "YYYY-MM-DD".
                Requires Homebox v0.26.0+; ignored on older Homebox versions.
            warranty_details: Warranty details/notes. Requires Homebox
                v0.26.0+; ignored on older Homebox versions.
            purchase_price: Purchase price.
            purchase_date: Purchase date, as "YYYY-MM-DD". Requires
                Homebox v0.26.0+; ignored on older Homebox versions.
            purchase_from: Where the item was purchased. Requires Homebox
                v0.26.0+; ignored on older Homebox versions.
            sold_date: Date the item was sold, as "YYYY-MM-DD". Requires
                Homebox v0.26.0+; ignored on older Homebox versions.
            sold_to: Who the item was sold to. Requires Homebox v0.26.0+;
                ignored on older Homebox versions.
            sold_price: Sale price. Requires Homebox v0.26.0+; ignored on
                older Homebox versions.
            sold_notes: Notes about the sale. Requires Homebox v0.26.0+;
                ignored on older Homebox versions.
            notes: Notes/observations.

        Returns:
            Updated item with all fields.
        """
        return await client.update_item(
            item_id=item_id,
            name=name,
            description=description,
            quantity=quantity,
            location_id=location_id,
            labels=labels,
            insured=insured,
            archived=archived,
            asset_id=asset_id,
            serial_number=serial_number,
            model_number=model_number,
            manufacturer=manufacturer,
            lifetime_warranty=lifetime_warranty,
            warranty_expires=warranty_expires,
            warranty_details=warranty_details,
            purchase_price=purchase_price,
            purchase_date=purchase_date,
            purchase_from=purchase_from,
            sold_date=sold_date,
            sold_to=sold_to,
            sold_price=sold_price,
            sold_notes=sold_notes,
            notes=notes,
        )

    @mcp.tool()
    async def homebox_move_item(item_id: str, location_id: str) -> dict[str, Any]:
        """Move an item to another location.

        Convenient shortcut to change an item's location.

        Args:
            item_id: Item ID (UUID) to move.
            location_id: New location ID (UUID).

        Returns:
            Updated item with the new location.
        """
        return await client.move_item(item_id, location_id)

    @mcp.tool()
    async def homebox_add_item_attachment(
        item_id: str,
        file_base64: str,
        filename: str | None = None,
        attachment_type: str | None = None,
        primary: bool = False,
    ) -> dict[str, Any]:
        """Attach a file to an item: a photo, or a document like a manual,
        warranty, or receipt (e.g. a PDF).

        The file must be base64-encoded (e.g. from a file read as bytes and
        base64-encoded, not raw binary — MCP tool arguments are JSON). Only
        JPEG, PNG, GIF, WEBP, HEIC images and PDF documents are accepted,
        verified from the actual file content rather than the filename, and
        uploads over 10 MB are rejected.

        Args:
            item_id: Item ID (UUID) to attach the file to.
            file_base64: The file content, base64-encoded.
            filename: File name to store, with extension (optional; a name
                is generated from the detected format if omitted).
            attachment_type: How Homebox should classify the file: "photo",
                "manual", "warranty", "receipt", or "attachment" (optional;
                defaults to "photo" for images and "attachment" for
                documents like PDFs).
            primary: Set this as the item's primary/cover photo (only
                meaningful for images).

        Returns:
            The updated item, including its attachments list.
        """
        try:
            data = base64.b64decode(file_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"file_base64 is not valid base64 data: {exc}") from exc
        return await client.add_item_attachment(item_id, data, filename, attachment_type, primary)

    @mcp.tool()
    async def homebox_add_item_attachment_from_url(
        item_id: str,
        url: str,
        filename: str | None = None,
        attachment_type: str | None = None,
        primary: bool = False,
    ) -> dict[str, Any]:
        """Attach a file to an item by downloading it from a URL.

        Use this when YOU found the file yourself (e.g. a product photo from
        a web search, or a manual/spec PDF linked from a manufacturer's
        page) — not when the user has shared/uploaded a file in the
        conversation. For a file the user supplied, use
        homebox_add_item_attachment with base64-encoded bytes instead; this
        tool takes a URL and downloads it server-side.

        The URL must be http:// or https:// and resolve to a public address
        (internal/private/loopback addresses are refused, including through
        redirects). The download is capped at 10 MB and, like
        homebox_add_item_attachment, only JPEG, PNG, GIF, WEBP, HEIC images
        and PDF documents are accepted — verified from the actual downloaded
        content, not the URL or any server-supplied content-type.

        Args:
            item_id: Item ID (UUID) to attach the file to.
            url: Direct http(s) URL to the image or document.
            filename: File name to store, with extension (optional; derived
                from the URL if it has one, else generated from the
                detected format).
            attachment_type: How Homebox should classify the file: "photo",
                "manual", "warranty", "receipt", or "attachment" (optional;
                defaults to "photo" for images and "attachment" for
                documents).
            primary: Set this as the item's primary/cover photo (only
                meaningful for images).

        Returns:
            The updated item, including its attachments list.
        """
        return await client.add_item_attachment_from_url(
            item_id, url, filename, attachment_type, primary
        )

    @mcp.tool()
    async def homebox_delete_item(item_id: str) -> str:
        """Remove an item from the inventory.

        WARNING: This action is permanent.

        Args:
            item_id: Item ID (UUID) to remove.

        Returns:
            Confirmation message.
        """
        await client.delete_item(item_id)
        return f"Item {item_id} successfully removed."

    # =========================================================================
    # Label Tools
    # =========================================================================

    @mcp.tool()
    async def homebox_list_labels() -> list[dict[str, Any]]:
        """List all labels/tags in the inventory.

        Labels are used to categorize and organize items.

        Returns:
            List of labels with id, name, description, and color.
        """
        labels = await client.get_labels()
        return [
            {
                "id": label.get("id"),
                "name": label.get("name"),
                "description": label.get("description", ""),
                "color": label.get("color", ""),
                "item_count": label.get("itemCount", 0),
            }
            for label in labels
        ]

    @mcp.tool()
    async def homebox_create_label(
        name: str,
        description: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        """Create a new label/tag.

        Labels are useful for categorizing items (e.g., "Electronics",
        "Tools", "Documents").

        Args:
            name: Label name (required).
            description: Label description (optional).
            color: Color in hexadecimal format (e.g., "#FF5733").

        Returns:
            Created label with all fields.
        """
        return await client.create_label(name, description, color)

    @mcp.tool()
    async def homebox_update_label(
        label_id: str,
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing label.

        Args:
            label_id: Label ID (UUID) to update.
            name: New name (optional).
            description: New description (optional).
            color: New color in hexadecimal format (optional).

        Returns:
            Updated label.
        """
        return await client.update_label(label_id, name, description, color)

    @mcp.tool()
    async def homebox_delete_label(label_id: str) -> str:
        """Remove a label from the inventory.

        Associated items will not be removed, they will just lose the label.

        Args:
            label_id: Label ID (UUID) to remove.

        Returns:
            Confirmation message.
        """
        await client.delete_label(label_id)
        return f"Label {label_id} successfully removed."

    # =========================================================================
    # Statistics Tools
    # =========================================================================

    @mcp.tool()
    async def homebox_get_statistics() -> dict[str, Any]:
        """Get inventory statistics.

        Returns counts and totals useful for getting an overview of
        the inventory.

        Returns:
            Statistics including item count, locations, labels,
            and total value.
        """
        return await client.get_statistics()
