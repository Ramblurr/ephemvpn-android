
package com.binaryelysium.ephemvpn;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.os.Bundle;

public class RpcServerLauncher extends Activity {

    public static final ComponentName SL4A_SERVICE_COMPONENT_NAME = new ComponentName(
            "com.binaryelysium.ephemvpn", "com.binaryelysium.ephemvpn.RpcServerService");

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Forward the intent that launched us to start the service.
        Intent intent = getIntent();
        intent.setComponent(SL4A_SERVICE_COMPONENT_NAME);
        startService(intent);
        finish();
    }
}
