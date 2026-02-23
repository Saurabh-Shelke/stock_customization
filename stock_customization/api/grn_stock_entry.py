# import frappe

# def create_stock_entry_from_grn(doc, method):

#     # create stock entry
#     se = frappe.new_doc("Stock Entry")

#     se.stock_entry_type = "Subcontracting Finished"
#     se.company = doc.company
#     se.posting_date = doc.posting_date
#     se.posting_time = doc.posting_time

#     source_wh = doc.custom_source_warehouse
#     target_wh = doc.custom_target_warehouse

#     for d in doc.items:
#         se.append("items", {
#             "item_code": d.item_code,
#             "qty": d.qty,
#             "uom": d.uom,
#             "stock_uom": d.stock_uom,
#             "conversion_factor": d.conversion_factor or 1,
#             "t_warehouse": target_wh,

#             # store temporarily
#             "custom_source_warehouse": source_wh
#         })

#     se.insert(ignore_permissions=True)
#     se.submit()

#     frappe.msgprint(f"Stock Entry Created: {se.name}")


import frappe

def create_se_from_grn(doc, method):

    source_wh = doc.get("custom_source_warehouse")
    target_wh = doc.get("custom_target_warehouse")

    if not source_wh or not target_wh:
        frappe.throw("Please set Source and Target Warehouse in GRN")

    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Subcontracting Finished"
    se.company = doc.company
    se.posting_date = doc.posting_date
    se.posting_time = doc.posting_time

    # bypass validation restriction
    se.flags.ignore_validate = True

    for d in doc.items:

        conversion = d.conversion_factor or 1
        transfer_qty = d.qty * conversion

        se.append("items", {
            "item_code": d.item_code,
            "qty": d.qty,
            "uom": d.uom,
            "stock_uom": d.stock_uom,
            "conversion_factor": conversion,
            "transfer_qty": transfer_qty,   # 🔥 IMPORTANT
            "s_warehouse": source_wh,
            "t_warehouse": target_wh,
            "basic_rate": d.rate or 0,
            "valuation_rate": d.rate or 0
        })

    se.insert(ignore_permissions=True)
    # se.submit()

    # force store warehouses again (ERP removes internally)
    for item in se.items:
        frappe.db.set_value("Stock Entry Detail", item.name, "s_warehouse", source_wh)
        frappe.db.set_value("Stock Entry Detail", item.name, "t_warehouse", target_wh)

    # frappe.db.commit()
    # se.reload()
    # se.submit()
    frappe.enqueue(
        submit_stock_entry_background,
        queue="short",
        enqueue_after_commit=True,
        se_name=se.name,
        source_wh=source_wh,
        target_wh=target_wh
    )   

    frappe.msgprint(f"Stock Entry Created: {se.name}")


def submit_stock_entry_background(se_name, source_wh, target_wh):

    try:
        se = frappe.get_doc("Stock Entry", se_name)

        for item in se.items:
            frappe.db.set_value("Stock Entry Detail", item.name, "s_warehouse", source_wh)
            frappe.db.set_value("Stock Entry Detail", item.name, "t_warehouse", target_wh)

        frappe.db.commit()

        se.reload()
        se.submit()

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Stock Entry Auto Submit Failed")