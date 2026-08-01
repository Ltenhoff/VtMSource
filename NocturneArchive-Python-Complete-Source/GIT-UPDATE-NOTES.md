# PDF byte-preservation update

- Uses the uploaded four-page floral V20 interactive PDF as the Vampire master.
- Uses the uploaded three-page Pulp Cthulhu interactive PDF as the CoC master.
- New characters receive their own byte-for-byte working copy.
- Import, export, reset, and persistent storage use direct file copies.
- The application never recreates, rasterizes, flattens, or rewrites PDF pages.
- Native PDF downloads are copied back into the active character's stored sheet.
- Qt WebEngine rendering flags favor D3D11/ANGLE and disable Vulkan to reduce flicker.
