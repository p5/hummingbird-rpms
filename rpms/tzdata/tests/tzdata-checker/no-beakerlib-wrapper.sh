#!/bin/bash

failCounter=0
passCounter=0

rlJournalStart()
{
  timeStart=`date +%s.%N`
}

rlShowRunningKernel()
{
  printf ":: [ %s ] :: [   \e[36mLOG\e[0m    ] :: Kernel version: '%s'\n" `date +%s.%N` `uname -r`
}

rlAssertRpm()
{
  if rpm -q $1; then
    ((passCounter++))
    printf ":: [ %s ] :: [   \e[32mPASS\e[0m   ] :: Checking for the presence of %s rpm\n" `date +%s.%N` "$1"
    printf ":: [ %s ] :: [   \e[36mLOG\e[0m    ] ::   %s\n" `date +%s.%N` `rpm -q $1`
  else
    ((failCounter++))
    printf ":: [ %s ] :: [   \e[31;1mFAIL\e[0m   ] :: Checking for the presence of %s rpm\n" `date +%s.%N` "$1"
  fi
}

rlRun()
{
  eval $1
  retVal=$?
  if [ "$retVal" != "0" ]; then
    ((failCounter++))
    printf ":: [ %s ] :: [   \e[31;1mFAIL\e[0m   ] :: Command '%s'\n" `date +%s.%N` "$1"
  else
    ((passCounter++))
    printf ":: [ %s ] :: [   \e[32mPASS\e[0m   ] :: Command '%s'\n" `date +%s.%N` "$1"
  fi
  return $retVal
}

rlLogInfo()
{
  printf ":: [ %s ] :: [   \e[33mINFO\e[0m   ] :: %s\n" `date +%s.%N` "$1"
}

rlJournalPrintText()
{
  timeEnd=`date +%s.%N`
}

rlJournalEnd()
{
  printf '\n\n\n::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::\n'
  printf '::   TEST PROTOCOL\n'
  printf '::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::\n'
  printf '::   Duration: %s s\n' `bc <<< "$timeEnd - $timeStart"`
  printf '::   Assertions: %i good, %i bad\n::   RESULT: ' $passCounter $failCounter
  if [ "$failCounter" != "0" ]; then
    printf '\e[31;1mFAIL\e[0m\n'
  else
    printf '\e[32mPASS\e[0m\n'
  fi
}

rlFileSubmit(){ return 0; }

rlPhaseEnd(){ return 0; }

rlPhaseStartCleanup(){ return 0; }

rlPhaseStartSetup(){ return 0; }
