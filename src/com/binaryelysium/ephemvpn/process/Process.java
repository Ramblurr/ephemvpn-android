/*
 * Copyright (C) 2010 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not
 * use this file except in compliance with the License. You may obtain a copy of
 * the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */

/*
 * Copyright (C) 2012, Anthony Prieur & Daniel Oppenheim. All rights reserved.
 *
 * Original from SL4A modified to allow to embed Interpreter and scripts into an APK
 */

package com.binaryelysium.ephemvpn.process;

import com.binaryelysium.ephemvpn.StreamGobbler;
import com.binaryelysium.ephemvpn.StreamGobbler.StreamUpdate;
import com.binaryelysium.ephemvpn.config.GlobalConstants;
import com.googlecode.android_scripting.Exec;

import android.util.Log;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileDescriptor;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.concurrent.atomic.AtomicInteger;

public class Process {
    private static final int DEFAULT_BUFFER_SIZE = 8192;

    private final List<String> mArguments;

    private final Map<String, String> mEnvironment;

    private static final int PID_INIT_VALUE = -1;

    private File mBinary;

    private String mName;

    private long mStartTime;

    private long mEndTime;

    protected final AtomicInteger mPid;

    protected FileDescriptor mFd;

    protected OutputStream mOut;

    protected StreamGobbler mIn;

    protected File mLog;

    private int returnValue;

    public int getReturnValue() {
        return this.returnValue;
    }

    public Process() {
        mArguments = new ArrayList<String>();
        mEnvironment = new HashMap<String, String>();
        mPid = new AtomicInteger(PID_INIT_VALUE);
    }

    public void addArgument(String argument) {
        mArguments.add(argument);
    }

    public void addAllArguments(List<String> arguments) {
        mArguments.addAll(arguments);
    }

    public void putAllEnvironmentVariables(Map<String, String> environment) {
        mEnvironment.putAll(environment);
    }

    public void putEnvironmentVariable(String key, String value) {
        mEnvironment.put(key, value);
    }

    public void setBinary(File binary) {
        if (!binary.exists()) {
            throw new RuntimeException("Binary " + binary + " does not exist!");
        }

        mBinary = binary;
    }

    public Integer getPid() {
        return mPid.get();
    }

    public FileDescriptor getFd() {
        return mFd;
    }

    public OutputStream getOut() {
        return mOut;
    }

    public OutputStream getErr() {
        return getOut();
    }

    public File getLogFile() {
        return mLog;
    }

    public class FileStreamUpdate extends StreamUpdate {
        BufferedWriter os;
        public FileStreamUpdate(File file) throws IOException {
            this.os = new BufferedWriter(new FileWriter(file));

        }
        @Override
        public void update(String val) {
            try {
                os.write(val);
                Log.d("EPHVPN", val);
                os.flush();
            } catch (IOException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
            }

        }
    }

    public void start(final Runnable shutdownHook) {
        if (isAlive()) {
            throw new RuntimeException("Attempted to start process that is already running.");
        }

        String binaryPath = mBinary.getAbsolutePath();
        Log.i(GlobalConstants.LOG_TAG, "Executing " + binaryPath + " with arguments " + mArguments
                + " and with environment " + mEnvironment.toString());

        int[] pid = new int[1];
        String[] argumentsArray = mArguments.toArray(new String[mArguments.size()]);

        mLog = new File(String.format("%s/%s.log", getSdcardPackageDirectory() + "/", getName()));
        Log.d("EPHEM", mLog.getAbsolutePath());
        mFd = Exec.createSubprocess(binaryPath, argumentsArray, getEnvironmentArray(),
                getWorkingDirectory(), pid);
        mPid.set(pid[0]);
        mOut = new FileOutputStream(mFd);
        try {
            mIn = new StreamGobbler( new FileInputStream(mFd), new FileStreamUpdate(mLog));
            mStartTime = System.currentTimeMillis();

            new Thread(new Runnable() {
                @Override
                public void run() {
                    returnValue = Exec.waitFor(mPid.get());
                    mEndTime = System.currentTimeMillis();
                    int pid = mPid.getAndSet(PID_INIT_VALUE);
                    Log.d(GlobalConstants.LOG_TAG, "Process " + pid + " exited with result code "
                            + returnValue + ".");

                    try {
                        mOut.close();
                    } catch (IOException e) {
                        Log.e(GlobalConstants.LOG_TAG, e.getMessage());
                    }
                    if (shutdownHook != null) {
                        shutdownHook.run();
                    }
                }
            }).start();
        } catch (FileNotFoundException e) {
            e.printStackTrace();
        } catch (IOException e1) {
            // TODO Auto-generated catch block
            e1.printStackTrace();
        }
    }

    private String[] getEnvironmentArray() {
        List<String> environmentVariables = new ArrayList<String>();
        for (Entry<String, String> entry : mEnvironment.entrySet()) {
            environmentVariables.add(entry.getKey() + "=" + entry.getValue());
        }
        String[] environment = environmentVariables
                .toArray(new String[environmentVariables.size()]);
        return environment;
    }

    public void kill() {
        if (isAlive()) {
            android.os.Process.killProcess(mPid.get());
            Log.d(GlobalConstants.LOG_TAG, "Killed process " + mPid);
        }
    }

    public boolean isAlive() {
        return (mFd != null && mFd.valid()) && mPid.get() != PID_INIT_VALUE;
    }

    public String getWorkingDirectory() {
        return null;
    }

    public String getSdcardPackageDirectory() {
        return null;
    }

    public String getUptime() {
        long ms;
        if (!isAlive()) {
            ms = mEndTime - mStartTime;
        } else {
            ms = System.currentTimeMillis() - mStartTime;
        }
        StringBuilder buffer = new StringBuilder();
        int days = (int)(ms / (1000 * 60 * 60 * 24));
        int hours = (int)(ms % (1000 * 60 * 60 * 24)) / 3600000;
        int minutes = (int)(ms % 3600000) / 60000;
        int seconds = (int)(ms % 60000) / 1000;
        if (days != 0) {
            buffer.append(String.format("%02d:%02d:", days, hours));
        } else if (hours != 0) {
            buffer.append(String.format("%02d:", hours));
        }
        buffer.append(String.format("%02d:%02d", minutes, seconds));
        return buffer.toString();
    }

    public String getName() {
        return mName;
    }

    public void setName(String name) {
        mName = name;
    }
}
