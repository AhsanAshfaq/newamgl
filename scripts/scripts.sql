-------- 30-05-2018 ---------------
-- All things before now are updated on production

-- Added below query against IRA-38 -----
ALTER SEQUENCE public.amgl_order_line_id_seq RESTART WITH 10000

------ Added below query to update first_deposit_date against existing customer ---------
DROP TABLE
IF EXISTS PUBLIC.list;
SELECT ol.date_received,c.id INTO TABLE PUBLIC.list FROM amgl_customer AS c
	INNER JOIN amgl_order_line AS ol ON ol.customer_id = c.id
	WHERE ol.id = (
			SELECT id
			FROM amgl_order_line AS o
			WHERE o.customer_id = c.id
				AND is_master_records = False
			ORDER BY o.date_received limit 1
			);

SELECT *
FROM PUBLIC.list;

UPDATE amgl_customer b SET customer_first_deposit_date = a.date_received FROM PUBLIC.list AS a WHERE a.id = b.id;

UPDATE amgl_customer SET customer_first_deposit_date = '01/01/2000' WHERE customer_first_deposit_date IS NULL;

--------------------------- Added below query for updating transaction_detail_sort_date to update the date field for sorting -----------------------------------------

UPDATE amgl_order_line set transaction_detail_sort_date = date_received;

UPDATE amgl_order_line b
SET transaction_detail_sort_date = a.date_create
FROM amgl_metal_movement AS a
WHERE a.id = b.metal_movement_id;



--------------------------- Added below query for updating is_grace_period_value_ever_given against those customers where grace period value is provided --------------------------


DROP TABLE
IF EXISTS PUBLIC.list;
SELECT grace_period,id INTO TABLE public.list FROM amgl_customer WHERE grace_period > 0;

SELECT * FROM PUBLIC.list;

UPDATE amgl_customer b SET is_grace_period_value_ever_given = True FROM PUBLIC.list AS a WHERE a.id = b.id;
 ----------------------------------------------------------------------------------------------------------

 ------------ Query to remove foriegn keys as they are not in use after review users manual ---------------

 ALTER TABLE amgl_metal_movement DROP CONSTRAINT amgl_metal_movement_vault_complete_added_by_fkey;

 ALTER TABLE amgl_metal_movement DROP CONSTRAINT amgl_metal_movement_vault_review_added_by_fkey;

-----------------------------------------------------------------------------------------------------------