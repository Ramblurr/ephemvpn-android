package com.binaryelysium.ephemvpn.config;

import com.binaryelysium.ephemvpn.R;
import com.binaryelysium.ephemvpn.R.xml;

import android.os.Bundle;
import android.preference.PreferenceFragment;

public class AmazonSettings extends PreferenceFragment {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // TODO Auto-generated method stub
        super.onCreate(savedInstanceState);

        // Load the preferences from an XML resource
        addPreferencesFromResource(R.xml.pref_amazon);
    }

}