//! Pure-Rust reader and writer for Microsoft Access Jet 3/4 and ACE (`.mdb` / `.accdb`) databases.
//!
//! `jackcess_rs` provides binary-level compatibility with Java Jackcess
//! (`com.healthmarketscience.jackcess`, Apache-2.0):
//! - Reading Jet 3 (`V1997`), Jet 4 (`V2000`/`V2003`), and ACE (`V2007`–`V2019`) tables, columns, indexes, and LVAL chains.
//! - Creating new Jet 4 (`V2000`) `.mdb` databases, tables, and multi-page TDEFs.
//! - Row insertion, in-place and overflow (`0x4000`) updates, and row deletion (`0xC000`).
//! - User-table B-tree index encoding, prefix compression, leaf-to-node (`0x03`) splitting, and `unique` / `required` / `ignore_nulls` constraints.
//! - `LvProp` (`MR2\0` / `KKD\0`) `PropertyMap` reading and writing for tables, columns, indexes, and database summary/user-defined properties.

pub mod empty_mdb;
pub mod jackcess;
pub mod mdb;

pub use empty_mdb::get_empty_v2000_mdb;
pub use jackcess::{
    add_rows_to_table, add_rows_to_table_ex, create_empty_mdb_file, create_table_in_data,
    decode_lvprop_bytes, delete_row_in_table, encode_lvprop_bytes, execute_jackcess_op,
    get_object_properties, restore_mdb_from_schema_value, save_object_properties,
    update_row_in_table,
};
pub use mdb::{
    discover_tables, discover_user_tables, export_full_schema_from_file, parse_table,
    parse_table_ver, ColumnDef, IndexDef, JetVersion, RealIndexDef, TableDef,
};
