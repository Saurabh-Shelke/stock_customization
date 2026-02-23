import frappe

def allow_source_warehouse(doc, method):

    # run only for subcontracting finished
    if doc.stock_entry_type != "Subcontracting Finished":
        return

    for d in doc.items:
        if d.get("custom_source_warehouse"):
            # 🔥 FORCE SET SOURCE WAREHOUSE
            d.s_warehouse = d.custom_source_warehouse