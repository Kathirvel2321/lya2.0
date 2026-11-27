# Connect a Windows laptop to your LYA

The linked laptop launcher opens the conversation from LYA’s private phone service. The service keeps up to five recent text exchanges encrypted and shares them with approved laptops and the paired phone. Use the same linked launcher on the home laptop to continue that conversation there.

1. Connect the laptop and phone to your private network. Install the linked launcher’s Python dependencies inside the checkout from PowerShell.

   ```powershell
   py -3 -m venv .venv-ui
   .\.venv-ui\Scripts\python.exe -m pip --disable-pip-version-check install --no-cache-dir qrcode==8.2 pywin32
   ```

   If `.venv-ui` already exists, use its Python and run the second command only.
2. Run `launch-lya-linked.cmd`. Select **Connect to my LYA** using the private HTTPS address that already opens the LYA phone app.
3. Scan the QR on the laptop with your phone. Compare the laptop name and six-digit code, then approve with the phone service’s existing passkey.
4. Reopen the launcher to resume chat. Use **Refresh** to load turns from the phone or another linked laptop. On the phone, **Connection → Refresh synced chat** loads the same conversation.
5. To remove a laptop, open **Connection → Verify owner → Linked devices** on the phone, then unlink that laptop. Clearing the saved link on the laptop removes its local credential. Use the phone to revoke the service-side link.

The launcher keeps only its Windows-protected credential at `.lya-linked/device.dpapi`, a Git-ignored path in the checkout. Conversation is displayed in memory. The service supplies replies using its configured inference and holds the history. Both clients need a reachable service.

## Service setup

Update the existing private mobile service using the maintained mobile bundle. In `/etc/lya-connect.json`, set `linked_history_key` to the absolute path of a Fernet key file readable by the service account with mode `0600`. Create and retain that key through the host’s protected key provisioning. Keep the service behind private Tailscale HTTPS and retain the owner’s existing paired-phone passkey. Linked chat uses the service’s existing conversational inference path.

Only conversations sent through the enabled phone service or the linked launcher enter synced history. The original native launcher’s existing local conversations, memories, vault, and device controls are outside this linked conversation. A first service pairing is required for accounts that have never set up the private phone service.
