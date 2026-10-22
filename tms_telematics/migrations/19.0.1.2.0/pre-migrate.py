def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'tms_telematics_reading'
        """
    )
    if not cr.fetchone():
        return
    # Demo data is loaded before post-migrate. Drop the xmlids first so the
    # loader does not try to browse the model that this upgrade removes.
    cr.execute("DELETE FROM ir_model_data WHERE model = 'tms.telematics.reading'")
    cr.execute(
        "ALTER TABLE tms_telematics_reading RENAME TO tms_telematics_reading_merge"
    )
